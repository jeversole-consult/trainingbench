# Spreadsheet Calculator

TrainingBench can invoke formulas from an attached Excel
spreadsheet during chat. When a user asks a numerical question
and TB is configured with a spreadsheet, the system tries the
calculator *before* falling through to the RAG retrieval path —
giving a deterministic, formula-evaluated answer when one is
available.

Backend: `backend/api/spreadsheet_calculator.py`
(`SpreadsheetCalculator` class, openpyxl + pandas).

## What it does

1. Parses the question for sheet / category / column keywords.
2. Locates the matching cell or formula in the attached
   spreadsheet.
3. Evaluates the formula (via pandas / openpyxl) and returns the
   answer, formatted per the cell's number format when present.
4. If no match, returns `None` and the chat flow falls through to
   the RAG + LLM path normally.

Query types the calculator handles today:

- **Category lookup**: "What is X for the Y category?" → finds
  the row + column and returns the value.
- **Totals**: "What is the total X?" → aggregates a column.
- **Summaries**: "Summarize the X sheet" → emits a short summary
  of the sheet's contents.

## How to attach a spreadsheet

The calculator is service-wide today (one spreadsheet per TB
instance) and configured via an environment variable before the
service starts.

```bash
# In your deployment env or .env
export TB_SPREADSHEET_PATH=/path/to/your/workbook.xlsx
```

Restart the TB service. On boot you should see:

```
Spreadsheet calculator loaded from: /path/to/your/workbook.xlsx
```

If the file is missing, unreadable, or not `.xlsx`, TB logs a
warning and degrades to RAG-only mode — no crash.

## Known limitations

- **`.xlsx` only.** Other formats (`.xls`, `.ods`, `.csv`) are
  not supported. Pre-existing finding from TB-US-037; convert to
  `.xlsx` first if you need to use another source.
- **One spreadsheet per service instance.** Per-agent
  attachments are not wired up in v0.1; all agents share the
  spreadsheet configured by `TB_SPREADSHEET_PATH`. Per-agent
  calculator attachment is tracked as a candidate follow-up to
  TB-US-088.
- **Formula support follows openpyxl + pandas evaluation
  semantics.** Most spreadsheet functions evaluate correctly;
  external references, macro-driven cells, and unusual
  functions may not.

## Example queries (for a workbook with a `Loans` sheet)

```
"What is the monthly payment for category 'Auto'?"
"What is the total interest on the Auto loan?"
"Summarize the Loans sheet."
```

## When the calculator misses

If your question doesn't match any of the three query types, or
TB can't locate the relevant cell, the calculator silently
returns `None` and the RAG + LLM path answers the question
normally. The user never sees a calculator error — just an
LLM-sourced answer instead of a formula-sourced one.

## Related

- TB-US-037 — Wire `spreadsheet_calculator` into `/query`
  (backend foundation; shipped 2026-10-14)
- TB-US-086 — Backend feature audit (surfaced this capability as
  dormant in the UI)
- TB-US-088 — This story: Chat-tab hint + this doc page (Option
  A). Option B (per-agent attachment UI) remains a candidate
  follow-up.
