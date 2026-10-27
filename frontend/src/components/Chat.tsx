import { useEffect, useRef, useState } from "react";
import { askQuestion, SAMPLE_QUESTIONS, type Answer } from "../api";

interface Props {
  documentId: string;
}

interface Message {
  question: string;
  answer?: Answer;
  error?: string;
}

export default function Chat({ documentId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [waiting, setWaiting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, waiting]);

  async function ask(question: string) {
    question = question.trim();
    if (!question || waiting) return;
    setText("");
    setWaiting(true);
    setMessages((old) => [...old, { question }]);
    let reply: Message;
    try {
      const answer = await askQuestion(documentId, question);
      reply = { question, answer };
    } catch (e) {
      reply = { question, error: e instanceof Error ? e.message : "Could not get an answer." };
    }
    setMessages((old) => [...old.slice(0, -1), reply]);
    setWaiting(false);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    ask(text);
  }

  return (
    <section className="chat card" aria-label="Chat">
      <div className="thread">
        {messages.length === 0 && (
          <div className="empty">
            <h2>Ask a question</h2>
            <p className="muted">Answers come from your document, with sources.</p>
            <div className="chips">
              {SAMPLE_QUESTIONS.map((q) => (
                <button key={q} className="chip" onClick={() => ask(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i}>
            <div className="bubble user">{m.question}</div>
            {m.answer && <AnswerView answer={m.answer} />}
            {m.error && (
              <div className="bubble reply error" role="alert">
                {m.error}
              </div>
            )}
            {!m.answer && !m.error && (
              <div className="bubble reply" role="status" aria-label="Searching the document">
                <span className="dots">
                  <span />
                  <span />
                  <span />
                </span>
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form className="ask-form" onSubmit={handleSubmit}>
        <label htmlFor="question" className="visually-hidden">
          Your question
        </label>
        <input
          id="question"
          type="text"
          placeholder="Ask something about the document…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="button" type="submit" disabled={waiting || !text.trim()}>
          Ask
        </button>
      </form>
    </section>
  );
}

function AnswerView({ answer }: { answer: Answer }) {
  if (!answer.evidence_found) {
    return (
      <div className="bubble reply not-found">
        <strong>Not found in document</strong>
        <div>{answer.answer}</div>
      </div>
    );
  }
  return (
    <div className="bubble reply">
      <div>{answer.answer}</div>
      {answer.citations.length > 0 && (
        <div className="sources">
          {answer.citations.map((c, i) => (
            <div key={i} className="source">
              <div className="source-page">Page {c.page}</div>
              <div>{c.snippet}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
