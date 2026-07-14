# Managing documents

The **Manage Documents** tab shows every document currently in
the active database. Use it to organise files into folders,
filter the list to find something, and remove documents you no
longer want.

## What you see

The tab lists each document with its name, source (upload or
scrape), size or chunk count, and the folder it belongs to (if
any). The header includes controls for filtering and creating
new folders.

## Filtering

- **Filter by Folder** — pick a folder from the dropdown to
  show only its documents. Choose "All Folders" to reset.

## Folders

Folders group related documents together for organisational
purposes. They do not affect retrieval — a question against
the active database still searches every document regardless
of which folder it lives in — but they make the list easier
to navigate.

To create a folder, use the **+ Create New Folder** button and
give it a name. To move a document into a folder, use the
per-document controls on that document's row.

## Removing a document

Each document row includes a delete action. Deleting a document:

- Removes it from the list.
- Removes its chunks from the vector store, so it will no
  longer show up in retrieval or search results.

Deletion is scoped to the active database. If the same file
is uploaded to a different database, that copy is unaffected.

Deletion is not reversible from the UI. If you delete
something by mistake, you will need to re-upload it.

## Tips

- **Rename before uploading.** File names carry through into
  citations, so a clear filename like
  `Q3-2026-financial-report.pdf` is easier to work with than
  `scan_004_final_v2.pdf`.
- **Use folders sparingly.** Two or three folders per database
  is usually enough. Deep folder hierarchies do not add value
  because retrieval is content-based, not folder-based.
