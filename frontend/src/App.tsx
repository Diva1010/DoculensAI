import { useState } from "react";
import Dropzone from "./components/Dropzone";
import SummaryCard from "./components/SummaryCard";
import Chat from "./components/Chat";
import { deleteDocument, type UploadedDoc } from "./api";

export default function App() {
  const [doc, setDoc] = useState<UploadedDoc | null>(null);

  async function clearDocument() {
    if (!doc) return;
    try {
      await deleteDocument(doc.document_id);
    } catch {
      // the server may be gone, still go back to the start
    }
    setDoc(null);
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo">
          <span className="logo-mark">D</span>
          DocuLens AI
        </div>
        <span className="badge">Runs locally. Your files never leave this computer.</span>
      </header>

      {doc === null ? (
        <main className="landing">
          <h1>Ask your documents anything</h1>
          <p className="subtitle">
            Upload a PDF or text file to get a summary and answers with sources.
          </p>
          <Dropzone onUploaded={setDoc} />
        </main>
      ) : (
        <main className="workspace">
          <aside className="sidebar">
            <div className="card doc-card">
              <div className="doc-info">
                <div className="doc-name" title={doc.filename}>
                  {doc.filename}
                </div>
                <div className="muted">
                  {doc.page_count} page{doc.page_count === 1 ? "" : "s"}
                </div>
              </div>
              <button className="button secondary" onClick={clearDocument}>
                Clear
              </button>
            </div>
            <SummaryCard documentId={doc.document_id} />
          </aside>
          <Chat documentId={doc.document_id} />
        </main>
      )}
    </div>
  );
}
