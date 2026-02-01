# Testing the RAG System (Learning Books)

The system does **not** ship with pre-processed books. You must **upload your reference documents**, then **process** and **index** them before you can search or chat.

---

## 1. Set project ID for learning books (recommended)

- Open **Settings** in the frontend (sidebar).
- Set **Project ID** to **10** (reserved for the learning books corpus).
- This enables:
  - Book-sized chunking (2000 chars, 200 overlap) when you process.
  - Hybrid search (dense + BM25) when you search/chat.
  - BM25 index built automatically after you push to index.

You can keep project ID **1** for other documents; use **10** for your AI/Data Science references.

---

## 2. Ingest your books (3 steps)

### Step 1: Upload

1. Go to **Upload & Process** in the sidebar.
2. Upload your reference files (PDF, TXT, MD, DOCX, etc.).
3. Wait until each file shows as **uploaded**.

### Step 2: Process

1. Optionally set **Chunk size** and **Overlap** (for project **10** the backend uses book defaults: 2000 / 200).
2. Check **Reset existing chunks before processing** if you want to reprocess from scratch.
3. Click **Process**.
4. Wait for the success message (e.g. “Inserted N chunks from M files”).

### Step 3: Index (push)

1. Check **Reset existing index before pushing** if you want a fresh vector + BM25 index.
2. Click **Push to index**.
3. Wait for the success message (e.g. “Indexed N items”).  
   For project **10**, the BM25 index is built automatically after this step.

---

## 3. Test search and chat

- **Search**: Open **Search**, type a question or keyword, and run search. You should see results with scores and metadata (source, page, domain) when available.
- **Chat**: Open the **Chat** (home) page, ask a question; answers are generated from the indexed chunks (and for project 10, hybrid search is used).

---

## 4. Quick API check (optional)

With the backend at `http://localhost:8000`:

- Health: `GET http://localhost:8000/`
- Docs: `http://localhost:8000/docs`
- Upload: `POST /api/v1/data/upload/10` (form-data: `file`)
- Process: `POST /api/v1/data/process/10` (body: `{"chunk_size": 2000, "overlap_size": 200, "Do_reset": 0}`)
- Push: `POST /api/v1/nlp/index/push/10` (body: `{"do_reset": false}`)
- Search: `POST /api/v1/nlp/index/search/10` (body: `{"text": "your query", "limit": 5}`)
- Answer: `POST /api/v1/nlp/index/answer/10` (body: `{"text": "your question", "limit": 5}`)

Replace **10** with your project ID if different.

---

## Summary

| Step   | Action           | Where              |
|--------|------------------|--------------------|
| 1      | Set Project ID 10| Settings           |
| 2      | Upload files     | Upload & Process   |
| 3      | Process          | Upload & Process → Process |
| 4      | Push to index    | Upload & Process → Push to index |
| 5      | Search / Chat    | Search, Chat       |

Books are **not** pre-loaded; uploading and running Process + Push to index is required before search and chat will return results from your references.
