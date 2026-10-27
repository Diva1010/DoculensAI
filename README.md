# DocuLens AI

Upload a PDF or TXT file, get a summary, and ask questions about it. Answers come with the exact sentence from the document that supports them. If the document doesn't contain the answer, the app says so instead of guessing.

Everything runs on your own computer. Documents are never sent to an outside service.

## How it works

1. **Read the file.** The text is pulled out page by page.
2. **Split it into chunks.** Each page is cut into pieces of about 800 characters, and each piece remembers its page number.
3. **Find the right chunks.** When you ask a question, the app scores every chunk against it (TF-IDF with word stemming) and keeps the top 3. If nothing matches well enough, it answers "not enough information" without calling the model at all.
4. **Ask the model.** The top chunks and your question go to a small local language model (`Qwen2.5-1.5B-Instruct`), which writes a one-sentence answer.
5. **Show the evidence.** The sources shown under each answer are the real sentences from the document, chosen by the code, never written by the model.

Summaries work in two passes: the model summarizes each ~3000-character section, then summarizes those notes into an overview and key points.

## Project structure

```
backend/
  main.py           API routes (FastAPI)
  reader.py         read PDF/TXT, split pages into chunks
  search.py         find the chunks that match a question
  ai.py             load the model, answer questions, summarize
  evaluate.py       run the test questions and print a score
  questions.json    17 test questions for the demo document
  test_doculens.py  automated tests
frontend/
  src/App.tsx                    page layout and state
  src/api.ts                     talks to the backend
  src/components/Dropzone.tsx    upload area
  src/components/SummaryCard.tsx summary panel
  src/components/Chat.tsx        questions and answers
  public/demo.txt                fictional demo document
requirements.txt
```

## API

| Method and path | What it does |
|---|---|
| `GET /health` | Check the server is running |
| `POST /documents` | Upload a file, returns a document id |
| `POST /documents/{id}/summary` | Summarize the document |
| `POST /documents/{id}/questions` | Ask a question, returns answer and sources |
| `DELETE /documents/{id}` | Remove the document from memory |

Documents are kept in memory only and disappear when the server restarts.

## Run it

You need Python 3.9+ and Node.js.

```bash
# backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
```

```bash
# frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The first question or summary downloads the model (about 3 GB), so the first run is slow.

Click **Try the demo document** to test without a file of your own.

## Tests

```bash
cd backend
python -m pytest      # 33 tests, the model is faked so they run fast
python evaluate.py    # runs 17 questions through the real model
```

## Results

Measured on a MacBook Air (Apple GPU) with the fictional demo document:

| | Result |
|---|---|
| Answerable questions answered correctly | 11 of 12 |
| Unanswerable questions correctly refused | 5 of 5 |

The prompt and the scoring rules were adjusted using this same question set, so treat these numbers as a rough guide, not a benchmark. A larger model (3B) scored the same as 1.5B but was about three times slower.

## Limitations

- **Search matches words, not meaning.** "How big is each plot?" fails because the text says "measures". Questions whose words don't appear in the document are often refused even when the answer is there.
- **Short questions need care.** A chunk must share enough words with the question to be considered.
- **The model can blend facts or drift.** For example, a summary called an admission letter an enrollment. Check the sources shown under each answer.
- **Summaries have no sources**, so they are harder to verify.
- **Scanned PDFs, tables and multi-column layouts** are not supported or are read imperfectly.
- **Only the first ~36,000 characters** of a long document are summarized.
- **Small test set.** 12 answerable questions on one document.
- Not for legal, medical or financial decisions.

## Model

`Qwen/Qwen2.5-1.5B-Instruct`, set in `backend/ai.py`. Check the license on its Hugging Face model card before reusing it.

## Built with

Python, FastAPI, PyMuPDF, scikit-learn, NLTK, Hugging Face Transformers, React, TypeScript, Vite.
