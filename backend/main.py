import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai import answer_question, summarize_document
from reader import FileError, read_pages, split_pages
from search import Searcher

app = FastAPI(title="DocuLens AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

documents = {}


class Question(BaseModel):
    question: str


def get_document(document_id):
    doc = documents.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found. Upload it again.")
    return doc


@app.get("/health")
def health():
    return {"status": "ok", "documents_loaded": len(documents)}


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    data = await file.read()
    try:
        pages = read_pages(file.filename or "", data)
    except FileError as e:
        raise HTTPException(status_code=400, detail=str(e))

    document_id = uuid.uuid4().hex
    documents[document_id] = {
        "name": file.filename,
        "pages": pages,
        "searcher": Searcher(split_pages(pages)),
    }
    return {
        "document_id": document_id,
        "filename": file.filename,
        "page_count": len(pages),
        "status": "ready",
    }


@app.post("/documents/{document_id}/summary")
def summary(document_id: str):
    doc = get_document(document_id)
    try:
        return summarize_document(doc["pages"])
    except Exception:
        raise HTTPException(status_code=500, detail="Could not generate a summary. Please try again.")


@app.post("/documents/{document_id}/questions")
def ask(document_id: str, body: Question):
    doc = get_document(document_id)
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please enter a question.")
    chunks = doc["searcher"].search(question)
    try:
        return answer_question(question, chunks)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not generate an answer. Please try again.")


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    get_document(document_id)
    del documents[document_id]
    return {"status": "deleted"}
