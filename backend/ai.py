import re

from transformers import pipeline

from reader import split_pages
from search import best_sentence

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
NO_ANSWER = "The document does not provide enough information to answer this question."
SECTION_CHARS = 3000
MAX_SECTIONS = 12

model = None


def get_model():
    global model
    if model is None:
        model = pipeline("text-generation", model=MODEL_NAME)
    return model


def generate(prompt, max_new_tokens=200):
    messages = [{"role": "user", "content": prompt}]
    output = get_model()(messages, max_new_tokens=max_new_tokens, do_sample=False)
    return output[0]["generated_text"][-1]["content"].strip()


def make_prompt(question, chunks):
    sources = []
    for number, chunk in enumerate(chunks):
        sources.append("[Source " + str(number + 1) + ", page " + str(chunk["page"]) + "]\n" + chunk["text"])
    return (
        "Answer the question using ONLY the sources below, in one short sentence. "
        "If the sources state or clearly imply the answer, give it, including yes or no answers. "
        "Only if the sources say nothing relevant, reply exactly: "
        '"' + NO_ANSWER + '"\n\n' + "\n\n".join(sources) + "\n\nQuestion: " + question
    )


def answer_question(question, chunks):
    if not chunks:
        return {"answer": NO_ANSWER, "citations": [], "evidence_found": False}

    answer = generate(make_prompt(question, chunks))

    citations = []
    seen = []
    for chunk in chunks:
        snippet = best_sentence(question, chunk["text"])
        key = " ".join(snippet.split()).lower()
        if key not in seen:
            seen.append(key)
            citations.append({"page": chunk["page"], "snippet": snippet})
    return {"answer": answer, "citations": citations, "evidence_found": True}


def summarize_document(pages):
    sections = split_pages(pages, max_chars=SECTION_CHARS, overlap=100)
    if not sections:
        raise ValueError("Nothing to summarize.")

    truncated = len(sections) > MAX_SECTIONS
    sections = sections[:MAX_SECTIONS]

    notes = []
    for section in sections:
        prompt = "Summarize the following text in 2 sentences. Use only the text.\n\n" + section["text"]
        notes.append(generate(prompt, max_new_tokens=100))

    combined = "\n".join("- " + note for note in notes)
    final = generate(
        "Below are notes on a document. Using only these notes, write:\n"
        "OVERVIEW: 2-3 sentences\n"
        "KEY POINTS: 3-5 short bullet points\n\n" + combined,
        max_new_tokens=250,
    )
    overview, key_points = parse_summary(final)
    return {"overview": overview, "key_points": key_points, "truncated": truncated}


def parse_summary(text):
    text = text.replace("**", "")
    head, _, tail = text.partition("KEY POINTS:")
    overview = head.replace("OVERVIEW:", "").strip()
    points = []
    for line in tail.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if re.search(r"[A-Za-z0-9]", line):
            points.append(line)
    return overview, points
