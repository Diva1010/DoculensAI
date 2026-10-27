import fitz
import pytest
from fastapi.testclient import TestClient

import ai
import main
import reader
from ai import NO_ANSWER, answer_question, parse_summary, summarize_document
from main import app, documents
from reader import FileError, read_pages, split_pages
from search import Searcher, best_sentence

client = TestClient(app)

ARTICLE = "The Amazon rainforest hosts about 390 billion trees and many species of jaguars."


# ---------- reader: reading files ----------

def test_txt_is_read():
    assert read_pages("a.txt", b"Hello world") == [{"page": 1, "text": "Hello world"}]


def test_pdf_is_read_from_memory():
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Hello pdf")
    pages = read_pages("a.pdf", pdf.tobytes())
    assert pages[0]["page"] == 1
    assert "Hello pdf" in pages[0]["text"]


def test_unsupported_type_rejected():
    with pytest.raises(FileError):
        read_pages("a.docx", b"x")


def test_empty_file_rejected():
    with pytest.raises(FileError):
        read_pages("a.txt", b"   ")


# ---------- reader: chunking ----------

def test_chunks_keep_page_numbers():
    pages = [{"page": 1, "text": "Alpha."}, {"page": 2, "text": "Beta."}]
    chunks = split_pages(pages)
    assert [c["page"] for c in chunks] == [1, 2]
    assert [c["id"] for c in chunks] == [0, 1]


def test_long_text_is_split_with_overlap():
    text = "\n\n".join(f"Paragraph number {i} " + "word " * 30 for i in range(10))
    chunks = split_pages([{"page": 1, "text": text}], max_chars=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(c["text"]) <= 400 + 50 + 2 for c in chunks)
    assert chunks[0]["text"][-30:] in chunks[1]["text"]


def test_empty_page_gives_no_chunks():
    assert split_pages([{"page": 1, "text": "   "}]) == []


def test_overlap_does_not_start_mid_word():
    text = "\n\n".join(f"Paragraph number {i} " + "word " * 30 for i in range(10))
    chunks = split_pages([{"page": 1, "text": text}], max_chars=400, overlap=50)
    for c in chunks[1:]:
        first = c["text"].split()[0]
        assert first in {"word", "Paragraph", "number"} or first.isdigit()


# ---------- search ----------

CHUNKS = [
    {"id": 0, "page": 1, "text": "The Amazon rainforest produces oxygen and hosts huge biodiversity."},
    {"id": 1, "page": 2, "text": "Solar panels convert sunlight into electricity using silicon cells."},
]


def test_relevant_chunk_ranks_first():
    results = Searcher(CHUNKS).search("How do solar panels work?")
    assert results[0]["id"] == 1
    assert results[0]["page"] == 2


def test_unrelated_question_returns_nothing():
    assert Searcher(CHUNKS).search("What is the capital of France?") == []


def test_no_chunks_raises():
    with pytest.raises(ValueError):
        Searcher([])


def test_single_shared_word_is_not_evidence():
    chunks = [{"id": 0, "page": 1, "text": "The world's rainforests hold many species of trees and birds."}]
    assert Searcher(chunks).search("who won the world cup") == []


def test_word_forms_match():
    chunks = [{"id": 0, "page": 1, "text": "The ecological importance of the Amazon is huge."}]
    assert Searcher(chunks).search("why is the amazon important") != []


def test_best_sentence_picks_matching_sentence():
    text = "Our community of Spartans is diverse. Academic Plan: Software Engineering, MS. We hope you choose us."
    assert "Software Engineering" in best_sentence("which academic plan was selected", text)


# ---------- ai: answers ----------

def fake_model(monkeypatch, reply="ok"):
    monkeypatch.setattr(ai, "get_model", lambda: (lambda messages, **kw: [{"generated_text": [{"content": reply}]}]))


def test_no_chunks_skips_model(monkeypatch):
    def boom():
        raise RuntimeError("model should not be called")

    monkeypatch.setattr(ai, "get_model", boom)
    result = answer_question("anything", [])
    assert result == {"answer": NO_ANSWER, "citations": [], "evidence_found": False}


def test_duplicate_citations_are_removed(monkeypatch):
    fake_model(monkeypatch)
    same = "The waiting list holds 38 households."
    chunks = [
        {"id": 0, "page": 1, "text": same},
        {"id": 1, "page": 1, "text": same + " More text here."},
    ]
    result = answer_question("how many households on the waiting list", chunks)
    assert len(result["citations"]) == 1
    assert set(result["citations"][0]) == {"page", "snippet"}


# ---------- ai: summaries ----------

def test_parse_splits_overview_and_points():
    text = "OVERVIEW: A short overview.\nKEY POINTS:\n- First point\n2. 390 billion trees"
    overview, points = parse_summary(text)
    assert overview == "A short overview."
    assert points == ["First point", "390 billion trees"]


def test_parse_handles_missing_format():
    overview, points = parse_summary("Just a plain reply.")
    assert overview == "Just a plain reply."
    assert points == []


def test_parse_strips_markdown_bold():
    text = "OVERVIEW: **** A real overview.\n\n**\nKEY POINTS:\n- *\n- **Topic:** a real point"
    overview, points = parse_summary(text)
    assert overview == "A real overview."
    assert points == ["Topic: a real point"]


def test_long_document_is_flagged_truncated(monkeypatch):
    monkeypatch.setattr(ai, "generate", lambda prompt, max_new_tokens=200: "OVERVIEW: x\nKEY POINTS:\n- y")
    long_page = "\n\n".join("Sentence number %d. " % i * 40 for i in range(300))
    result = summarize_document([{"page": 1, "text": long_page}])
    assert result["truncated"] is True


def test_empty_document_raises():
    with pytest.raises(ValueError):
        summarize_document([{"page": 1, "text": "   "}])


# ---------- API ----------

@pytest.fixture(autouse=True)
def clean_documents():
    documents.clear()
    yield
    documents.clear()


def upload(text=ARTICLE, name="a.txt"):
    return client.post("/documents", files={"file": (name, text.encode(), "text/plain")})


def fake_answer(question, chunks):
    citations = [{"page": c["page"], "snippet": c["text"][:50]} for c in chunks]
    return {"answer": "stub answer", "citations": citations, "evidence_found": True}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_txt_succeeds():
    r = upload()
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["page_count"] == 1
    assert body["document_id"]


def test_unsupported_file_type_rejected():
    r = upload(name="a.docx")
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


def test_empty_upload_rejected():
    r = upload(text="   ")
    assert r.status_code == 400
    assert "No readable text" in r.json()["detail"]


def test_oversized_file_rejected(monkeypatch):
    monkeypatch.setattr(reader, "MAX_SIZE_MB", 0)
    r = upload()
    assert r.status_code == 400
    assert "larger" in r.json()["detail"]


def test_question_with_evidence_returns_citations(monkeypatch):
    monkeypatch.setattr(main, "answer_question", fake_answer)
    doc_id = upload().json()["document_id"]
    r = client.post(f"/documents/{doc_id}/questions", json={"question": "how many trees are in the amazon"})
    assert r.status_code == 200
    body = r.json()
    assert body["evidence_found"] is True
    assert body["citations"][0]["page"] == 1


def test_question_without_evidence_skips_model():
    doc_id = upload().json()["document_id"]
    r = client.post(f"/documents/{doc_id}/questions", json={"question": "who won the world cup"})
    assert r.status_code == 200
    body = r.json()
    assert body["evidence_found"] is False
    assert body["answer"] == NO_ANSWER
    assert body["citations"] == []


def test_blank_question_rejected():
    doc_id = upload().json()["document_id"]
    r = client.post(f"/documents/{doc_id}/questions", json={"question": "   "})
    assert r.status_code == 400


def test_unknown_document_returns_404():
    r = client.post("/documents/does-not-exist/questions", json={"question": "hello"})
    assert r.status_code == 404


def test_delete_removes_document():
    doc_id = upload().json()["document_id"]
    assert client.delete(f"/documents/{doc_id}").status_code == 200
    r = client.post(f"/documents/{doc_id}/questions", json={"question": "trees"})
    assert r.status_code == 404


def test_summary_returns_result(monkeypatch):
    fake = {"overview": "o", "key_points": ["p"], "truncated": False}
    monkeypatch.setattr(main, "summarize_document", lambda pages: fake)
    doc_id = upload().json()["document_id"]
    r = client.post(f"/documents/{doc_id}/summary")
    assert r.status_code == 200
    assert r.json() == fake


def test_summary_failure_gives_friendly_error(monkeypatch):
    def boom(pages):
        raise RuntimeError("model crashed")

    monkeypatch.setattr(main, "summarize_document", boom)
    doc_id = upload().json()["document_id"]
    r = client.post(f"/documents/{doc_id}/summary")
    assert r.status_code == 500
    assert "try again" in r.json()["detail"]
