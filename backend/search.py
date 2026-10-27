import re

from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MIN_SCORE = 0.10
MIN_SHARED_WORDS = 2
TOP = 3

stemmer = PorterStemmer()


def get_words(text):
    result = []
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word not in ENGLISH_STOP_WORDS:
            result.append(stemmer.stem(word))
    return result


class Searcher:
    def __init__(self, chunks):
        if not chunks:
            raise ValueError("Cannot search with no chunks.")
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(analyzer=get_words)
        texts = [chunk["text"] for chunk in chunks]
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, question):
        question_vector = self.vectorizer.transform([question])
        scores = cosine_similarity(question_vector, self.matrix).ravel()
        question_words = set(get_words(question))

        found = []
        for i in scores.argsort()[::-1][:TOP]:
            chunk = self.chunks[i]
            shared = question_words & set(get_words(chunk["text"]))
            if scores[i] >= MIN_SCORE and len(shared) >= min(MIN_SHARED_WORDS, len(question_words)):
                found.append(chunk)
        return found


def best_sentence(question, text, max_chars=250):
    question_words = set(get_words(question))
    sentences = []
    for part in re.split(r"(?<=[.!?])\s+|\n+", text):
        if part.strip():
            sentences.append(part.strip())
    if not sentences:
        return text[:max_chars]

    best = sentences[0]
    best_count = -1
    for sentence in sentences:
        count = len(question_words & set(get_words(sentence)))
        if count > best_count:
            best = sentence
            best_count = count
    return best[:max_chars]
