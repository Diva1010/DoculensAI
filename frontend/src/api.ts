const API_URL = "http://127.0.0.1:8000";

export interface UploadedDoc {
  document_id: string;
  filename: string;
  page_count: number;
  status: string;
}

export interface Citation {
  page: number;
  snippet: string;
}

export interface Answer {
  answer: string;
  citations: Citation[];
  evidence_found: boolean;
}

export interface Summary {
  overview: string;
  key_points: string[];
  truncated: boolean;
}

export const SAMPLE_QUESTIONS = [
  "How much does a plot cost for residents?",
  "How many households are on the waiting list?",
  "What percentage of watering comes from rainwater?",
  "Who won the world cup?",
];

async function request(path: string, options?: RequestInit): Promise<Response> {
  try {
    return await fetch(API_URL + path, options);
  } catch {
    throw new Error("Cannot reach the server. Is the backend running?");
  }
}

async function getJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // no JSON in the response, keep the default message
    }
    throw new Error(message);
  }
  return res.json();
}

export async function uploadDocument(file: File): Promise<UploadedDoc> {
  const form = new FormData();
  form.append("file", file);
  const res = await request("/documents", { method: "POST", body: form });
  return getJson<UploadedDoc>(res);
}

export async function loadDemoDocument(): Promise<UploadedDoc> {
  const res = await fetch("/demo.txt");
  if (!res.ok) throw new Error("Could not load the demo document.");
  const text = await res.text();
  const file = new File([text], "demo-community-garden.txt", { type: "text/plain" });
  return uploadDocument(file);
}

export async function getSummary(documentId: string): Promise<Summary> {
  const res = await request("/documents/" + documentId + "/summary", { method: "POST" });
  return getJson<Summary>(res);
}

export async function askQuestion(documentId: string, question: string): Promise<Answer> {
  const res = await request("/documents/" + documentId + "/questions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return getJson<Answer>(res);
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await request("/documents/" + documentId, { method: "DELETE" });
  await getJson<unknown>(res);
}
