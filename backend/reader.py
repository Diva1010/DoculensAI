import re

import fitz

MAX_SIZE_MB = 20
MAX_CHARS = 800
OVERLAP = 150


class FileError(Exception):
    pass


def read_pages(filename, data):
    name = filename.lower()
    if name.endswith(".pdf"):
        suffix = ".pdf"
    elif name.endswith(".txt"):
        suffix = ".txt"
    else:
        ext = "." + name.rsplit(".", 1)[1] if "." in name else "none"
        raise FileError("Unsupported file type: " + ext + ". Use PDF or TXT.")

    if len(data) > MAX_SIZE_MB * 1024 * 1024:
        raise FileError("File is larger than " + str(MAX_SIZE_MB) + " MB.")

    if suffix == ".pdf":
        pages = read_pdf(data)
    else:
        pages = [{"page": 1, "text": data.decode("utf-8", errors="replace")}]

    has_text = False
    for page in pages:
        if page["text"].strip():
            has_text = True
    if not has_text:
        raise FileError("No readable text found. Scanned PDFs are not supported.")
    return pages


def read_pdf(data):
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        pages = []
        for number, page in enumerate(doc):
            pages.append({"page": number + 1, "text": page.get_text()})
        doc.close()
        return pages
    except Exception as e:
        raise FileError("Could not read PDF: " + str(e))


def split_pages(pages, max_chars=MAX_CHARS, overlap=OVERLAP):
    chunks = []
    for page in pages:
        for text in split_text(page["text"], max_chars, overlap):
            chunks.append({"id": len(chunks), "page": page["page"], "text": text})
    return chunks


def split_text(text, max_chars, overlap):
    pieces = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if paragraph:
            pieces.extend(split_long(paragraph, max_chars))

    chunks = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > max_chars:
            chunks.append(current)
            tail = current[-overlap:]
            if " " in tail:
                tail = tail.split(" ", 1)[1]
            current = tail + "\n\n" + piece
        elif current:
            current = current + "\n\n" + piece
        else:
            current = piece
    if current:
        chunks.append(current)
    return chunks


def split_long(paragraph, max_chars):
    if len(paragraph) <= max_chars:
        return [paragraph]
    parts = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        if current and len(current) + len(sentence) + 1 > max_chars:
            parts.append(current)
            current = sentence
        else:
            current = (current + " " + sentence).strip()
    if current:
        parts.append(current)
    return parts
