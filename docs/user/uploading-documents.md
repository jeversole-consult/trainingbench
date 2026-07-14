# Uploading documents

The **Upload Documents** tab lets you add files to the active
database. Once uploaded, the contents are searchable via the
Ask Questions tab and the Search Documents tab.

## Supported file types

- **PDF** (`.pdf`) — including scanned PDFs. Scanned PDFs go
  through OCR automatically if no text layer is present.
- **Word** (`.docx`)
- **PowerPoint** (`.pptx`)
- **Plain text** (`.txt`, `.md`, `.markdown`)
- **Spreadsheets** (`.csv`, `.xlsx`, `.xls`)

## How to upload

1. Confirm the **active database** at the top of the page is
   the one you want the files to end up in. If not, switch it
   before uploading.
2. Click the file input area on the Upload Documents tab and
   pick one or more files. You can also drag and drop.
3. Selected files show as a list. Review them; remove anything
   you did not mean to include.
4. Click **Upload Selected Files**. Progress and status appear
   on the tab; large files or many files at once may take a
   while.
5. When the upload finishes, the documents are chunked,
   embedded, and added to the active database's vector store.
   They are immediately queryable from Ask Questions and
   Search Documents.

## What happens behind the scenes

Each uploaded file is:

1. Parsed into text (with OCR fallback for scanned PDFs).
2. Split into overlapping chunks of a few hundred to a
   thousand tokens each. This lets the retrieval step find
   specific passages rather than whole documents.
3. Turned into numerical embeddings and stored in the vector
   database.

You do not need to manage any of this — it just happens on
upload. The one thing to know is that very large files are
split into many chunks, so they can take longer to ingest and
count toward the "chunks" number you see on the database
statistics.

## Tips

- **Group related documents in the same database.** If you
  have multiple topics or projects, use separate databases
  rather than mixing everything into one — retrieval quality
  goes up when the search space is topically coherent.
- **Prefer text-native files over scans.** OCR works but adds
  processing time and can produce transcription errors on
  poor scans. If a PDF has an existing text layer, keep it.
- **Check the file list before clicking Upload.** It is easy
  to accidentally include a wrong file. Uploaded files can
  be removed later from the Manage Documents tab, but
  catching a mistake before upload is faster.
