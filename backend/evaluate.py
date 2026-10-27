import json
import re
import sys
import time

from ai import NO_ANSWER, answer_question
from reader import read_pages, split_pages
from search import Searcher

doc_path = sys.argv[1] if len(sys.argv) > 1 else "../frontend/public/demo.txt"


def clean(text):
    return re.sub(r"\s+", " ", text.lower())


def mark(value):
    if value is None:
        return "-"
    return "yes" if value else "NO"


with open(doc_path, "rb") as f:
    pages = read_pages(doc_path, f.read())
searcher = Searcher(split_pages(pages))

with open("questions.json") as f:
    cases = json.load(f)

rows = []
start = time.time()
for case in cases:
    question = case["q"]
    expected = case["expected"]
    result = answer_question(question, searcher.search(question))
    answer = clean(result["answer"])
    snippets = clean(" ".join(c["snippet"] for c in result["citations"]))

    if expected is None:
        ok = (not result["evidence_found"]) or NO_ANSWER.lower() in answer
        rows.append({"q": question, "answerable": False, "ok": ok, "in_answer": None, "in_cite": None, "result": result})
    else:
        in_answer = expected.lower() in answer
        in_cite = case.get("cite", expected).lower() in snippets
        rows.append({"q": question, "answerable": True, "ok": in_answer and in_cite, "in_answer": in_answer, "in_cite": in_cite, "result": result})

print("\nRESULT   ANS  CITE  QUESTION")
for row in rows:
    status = "PASS" if row["ok"] else "FAIL"
    print(f"{status:8} {mark(row['in_answer']):4} {mark(row['in_cite']):5} {row['q']}")

answerable = [r for r in rows if r["answerable"]]
unanswerable = [r for r in rows if not r["answerable"]]
print("\nSUMMARY")
print(f"  Answerable:   {sum(r['ok'] for r in answerable)}/{len(answerable)} fully correct")
print(f"    answer has fact:   {sum(r['in_answer'] for r in answerable)}/{len(answerable)}")
print(f"    citation has fact: {sum(r['in_cite'] for r in answerable)}/{len(answerable)}")
print(f"  Unanswerable: {sum(r['ok'] for r in unanswerable)}/{len(unanswerable)} correctly refused")

duplicates = 0
for row in rows:
    citations = row["result"]["citations"]
    if len({c["snippet"] for c in citations}) < len(citations):
        duplicates += 1
print(f"  Questions with duplicate citations: {duplicates}")
print(f"  Total time: {time.time() - start:.0f}s")

failures = [r for r in rows if not r["ok"]]
if failures:
    print("\nFAILURES (read these):")
    for row in failures:
        print("- " + row["q"])
        print("    answer: " + row["result"]["answer"])
        for c in row["result"]["citations"]:
            print(f"    cite p{c['page']}: {c['snippet']}")
