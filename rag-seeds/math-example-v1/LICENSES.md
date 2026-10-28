# math-example-v1 RAG seed — license attribution

TB-US-057 Phase A. All reference documents in this directory are
either original Eversole Learning content (Apache 2.0) or derived
from permissively-licensed public-domain / Creative Commons sources
as noted below.

## Files

| File | Origin | License |
|---|---|---|
| `strategy-guide.md` | Original EL authorship; general problem-solving framework ("read-model-solve-check" pattern is common pedagogy, not copyrighted) | Apache 2.0 |
| `worked-examples.md` | Original EL authorship. Example problems invented for this file; not sourced from GSM8K or any other dataset. Patterns intentionally mirror common grade-school word-problem shapes (percent / ratio / rate / multi-step) | Apache 2.0 |
| `formula-sheet.md` | Original EL authorship. Formulas themselves are public-domain mathematical facts; the compilation and presentation here is EL-authored | Apache 2.0 |

## Notes

The RAG seed is deliberately small (3 reference docs) for the
TB-US-057 Phase B demonstration. Operators scaling the RAG for
their own domain should add additional reference docs via
`POST /rag-versions/{id}/ingest` after creating a new draft
version.

**Honest expectation-setting:** these reference docs may or may
not improve accuracy on GSM8K. Grade-school word problems are
language-parsing challenges more than formula-lookup challenges.
A null or negative delta on experiment E3 is also a valid finding
to document.
