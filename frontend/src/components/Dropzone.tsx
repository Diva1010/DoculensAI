import { useRef, useState } from "react";
import { loadDemoDocument, uploadDocument, type UploadedDoc } from "../api";

interface Props {
  onUploaded: (doc: UploadedDoc) => void;
}

export default function Dropzone({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function run(action: () => Promise<UploadedDoc>) {
    setUploading(true);
    setError("");
    try {
      onUploaded(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && !uploading) run(() => uploadDocument(file));
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      inputRef.current?.click();
    }
  }

  function handlePick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) run(() => uploadDocument(file));
  }

  return (
    <div className="dropzone-wrap">
      <div
        className={"dropzone" + (dragging ? " dragging" : "")}
        role="button"
        tabIndex={0}
        aria-label="Upload a PDF or TXT file. Click to browse or drop a file here."
        onClick={() => inputRef.current?.click()}
        onKeyDown={handleKey}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <div className="dropzone-icon" aria-hidden="true">
          ↑
        </div>
        <div className="dropzone-title">Drop a file here, or click to browse</div>
        <div className="muted">PDF or TXT, up to 20 MB. Scanned PDFs are not supported.</div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          hidden
          disabled={uploading}
          onChange={handlePick}
        />
      </div>

      <div className="divider">or</div>

      <button className="button secondary wide" disabled={uploading} onClick={() => run(loadDemoDocument)}>
        Try the demo document
      </button>

      {uploading && (
        <p className="muted center" role="status">
          Processing your document…
        </p>
      )}
      {error && (
        <p className="error center" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
