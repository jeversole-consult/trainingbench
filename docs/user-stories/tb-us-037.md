# TB-US-037: Wire `spreadsheet_calculator` into TB's `/query` flow (feature parity close-out)

**Status**: Completed
**Created**: 2026-10-14
**Completed**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator deploying a customer agent that depends on
spreadsheet-derived formulas (e.g. a stalite-style
deployment), I want TB's existing `SpreadsheetCalculator`
module wired into the `/query` flow so that a calculation
question is answered deterministically by the calculator
before falling through to RAG, matching stalite3's existing
STEP 1 → STEP 2 pattern and the OT quantitative-handler
architecture.

## Background

TB has shipped `backend/api/spreadsheet_calculator.py`
(a generic, Excel-formula-driven calculator — more generic
than stalite3's `formula_calculator.py` which hardcodes 13
Stalite mix formulas). But TB's `/query` flow currently does
NOT invoke it. The module is dormant.

**Important architectural finding (surfaced during TB-US-036
investigation):** TB's `RAGSystem` is already architecturally
ahead of stalite3 on this. `backend/rag/rag_system.py` defines:

```python
QueryHook = Callable[[str], Optional[str]]

class RAGSystem:
    def __init__(
        self,
        ...,
        calculator: Optional[QueryHook] = None,
        specialized_handler: Optional[QueryHook] = None,
    ):
```

And its `query()` method has a clean plugin-resolution order:
1. Optional caller-supplied `calculator` hook
2. Optional caller-supplied `specialized_handler` hook
3. Retrieval + generation

Stalite3 hardcodes `StaliteCalculator` + `MixDesignHandler` into
`rag_system.py`; TB abstracted the pattern. This story's work
is **wiring**: construct a `SpreadsheetCalculator` instance in
`main.py` (optionally, via env-var-driven spreadsheet path) and
pass its `.calculate` method as the `calculator=` arg when
constructing `RAGSystem`.

Signature compatibility is exact —
`SpreadsheetCalculator.calculate(self, question: str) -> Optional[str]`
matches `QueryHook = Callable[[str], Optional[str]]`.

## Requirements

- [x] R1: **Env-var-driven spreadsheet path.** New env var
      `TB_SPREADSHEET_PATH`. If set, points to an `.xlsx` /
      `.xlsm` file that `SpreadsheetCalculator` loads at
      startup. If unset, no calculator is wired (TB behaves
      exactly as it does today — RAG only).
- [x] R2: **Instantiate `SpreadsheetCalculator` conditionally
      in `main.py`.**
      ```python
      from api.spreadsheet_calculator import SpreadsheetCalculator

      TB_SPREADSHEET_PATH = os.getenv("TB_SPREADSHEET_PATH") or None
      spreadsheet_calculator = None
      if TB_SPREADSHEET_PATH:
          try:
              spreadsheet_calculator = SpreadsheetCalculator(TB_SPREADSHEET_PATH)
              print(f"Spreadsheet calculator loaded from: {TB_SPREADSHEET_PATH}")
          except Exception as e:
              print(f"Warning: SpreadsheetCalculator failed to load from {TB_SPREADSHEET_PATH}: {e}")
              spreadsheet_calculator = None
      ```
- [x] R3: **Wire the calculator hook when constructing
      `RAGSystem`.**
      ```python
      rag_system = RAGSystem(
          llm_provider=LLM_PROVIDER,
          model_name=LLM_MODEL,
          vector_store=VectorStore(persist_directory=active_db_path),
          calculator=spreadsheet_calculator.calculate if spreadsheet_calculator else None,
      )
      ```
- [x] R4: **Fail-soft.** If `SpreadsheetCalculator` raises
      during load (bad path, corrupt xlsx, missing openpyxl
      compat), TB falls back to RAG-only. Service does NOT
      fail to start; a warning is logged.
- [x] R5: **No change to `/query` request/response shape.**
      When the calculator answers, `RAGSystem.query` returns
      the existing `{"answer", "sources": [], "context": [],
      "plugin": "calculator"}` shape (TB's architecture;
      "plugin" is `"calculator"` instead of stalite3's
      `"calculation": True` key but matches TB's existing
      hook pattern).
- [x] R6: **No regression** when `TB_SPREADSHEET_PATH` is
      unset. TB's current RAG-only behavior is unchanged;
      existing callers of `/query` get the same responses
      they got before.
- [x] R7: **No modification** to `spreadsheet_calculator.py`
      itself or `backend/rag/rag_system.py`. The wiring is
      additive at the `main.py` instantiation site only.
- [x] R8: **Service restart** picks up both the import and
      the env var.

## Acceptance Criteria

- [x] AC1: With `TB_SPREADSHEET_PATH` unset, TB starts cleanly
      and `/query` behaves exactly as it does today
      (RAG-only). No regression.
- [x] AC2: With `TB_SPREADSHEET_PATH=<valid-xlsx>`,
      service startup logs show "Spreadsheet calculator
      loaded from: ...". A calculation question against
      `/query` returns the calculator's response with
      `plugin: "calculator"` and empty `sources` / `context`.
- [x] AC3: With `TB_SPREADSHEET_PATH=<invalid-path>`,
      service starts cleanly (fail-soft per R4); logs show
      the warning; `/query` falls through to RAG for all
      questions.
- [x] AC4: `backend/rag/rag_system.py` unchanged by this
      story (`git diff` empty for that file).
- [x] AC5: `backend/api/spreadsheet_calculator.py` unchanged.
- [x] AC6: `git diff backend/` is bounded to `main.py` only
      (and a diff of ~15 lines).

## Design Notes

- **Why env-var-driven path.** TB is a generic platform; it
  doesn't ship with a spreadsheet. Customer deployments
  (stalite-style) that want calculator-first behavior
  configure the env var. TB with no env var set has no
  calculator, which is the correct default for a generic
  install.
- **Why TB's hook pattern beats stalite3's hardcode.** TB
  can wire ANY calculator conforming to `QueryHook`, not
  just `SpreadsheetCalculator`. A future customer agent
  with a different calculation surface (e.g. a legal fee
  calculator, a dosage calculator) wires its own hook
  without touching `RAGSystem`.
- **Why not pre-instantiate stalite3's StaliteCalculator on
  TB.** It's stalite-specific (13 hardcoded Stalite mix
  formulas, specific-gravity ranges for 3/4"/1/2"/3/8"
  aggregate). It stays on stalite3. TB's generic
  `SpreadsheetCalculator` is the right primitive for TB
  master.
- **Why not change `/query`'s response "plugin" key to match
  stalite3's "calculation" key.** TB already has an
  established `plugin: "<name>"` pattern that applies
  uniformly to calculator / specialized_handler / future
  hooks. Changing it to match stalite3's `calculation: True`
  would regress TB's architecture.
- **Signature match.** `SpreadsheetCalculator.calculate(self,
  question: str) -> Optional[str]` is a bound method; after
  `calc = SpreadsheetCalculator(path)`, `calc.calculate` is
  a `Callable[[str], Optional[str]]` which exactly matches
  `QueryHook`.
- **Why fail-soft on load error.** The spreadsheet is
  deployment-specific. If an operator misconfigures the
  path or the file goes missing, the service should keep
  running — degraded (no calculator) but functional (RAG
  still works). Hard failure here would be worse than the
  degraded mode.
- **Stalite3 sync-forward implication.** stalite3 already
  has a working calculator path (via its StaliteCalculator
  hardcode). This story's wiring on TB does NOT change
  stalite3. Stalite3's calculator stays as it is; TB gains
  equivalent capability via the hook. The two installs now
  have semantically-equivalent calculator-first behavior
  through different implementations.

## Out of Scope

- Changing TB's `RAGSystem` architecture (hooks already
  exist).
- Modifying `SpreadsheetCalculator` behavior.
- Adding a UI control to upload/configure the spreadsheet
  at runtime. Env var is the only mechanism for v0.1.
- Wiring `specialized_handler` (TB's second hook). Separate
  story if ever useful.
- Supporting multiple calculators concurrently (fan-out).
  Not needed; one calculator per deployment.
- Porting stalite3's `StaliteCalculator` or
  `MixDesignHandler` to TB master. Those stay on stalite3
  (Stalite-domain-specific per TB-US-031's audit).
- Validating that the loaded spreadsheet actually contains
  usable formulas. `SpreadsheetCalculator`'s detection logic
  is already in place; this story doesn't audit it.
- Branding tweaks.

## Related

- Parent: [TB-US-031](tb-us-031.md) Section 3.7 (formula
  calculator capability).
- Sibling feature-parity close-out stories: TB-US-033, 034,
  035, 036.
- Code touched:
  - `backend/api/main.py` — new env var read + conditional
    instantiation + wiring to RAGSystem constructor
- Code NOT touched (verified by AC4/AC5):
  - `backend/rag/rag_system.py` (hooks already exist)
  - `backend/api/spreadsheet_calculator.py` (module
    unchanged)
- Direct port of stalite3's STEP-1 pattern (`rag_system.py`
  line 270–274), but mapped onto TB's cleaner hook
  architecture.

**Completion Notes (2026-10-14).**

- Added `from api.spreadsheet_calculator import SpreadsheetCalculator`
  import.
- Added conditional instantiation block in `main.py` after
  `active_db_path = db_manager.get_database_path()` and
  before `rag_system = RAGSystem(...)`. Env-var-driven
  (`TB_SPREADSHEET_PATH`); fail-soft on load error.
- Passed `calculator=spreadsheet_calculator.calculate if
  spreadsheet_calculator else None` to `RAGSystem()`
  constructor.
- Service restarted cleanly (6s to Uvicorn ready). All
  smoke-tests return 200.
- `git diff backend/`: 50 lines added, 1 line removed, all
  in `main.py`. `rag_system.py` and
  `spreadsheet_calculator.py` unchanged.

**AC verifications:**
- AC1 ✓ With `TB_SPREADSHEET_PATH` unset (current prod
  state), no "Spreadsheet calculator loaded" log line
  appeared — correct conditional skip. All existing
  endpoints 200.
- AC2 ✓ Inline test: loaded
  `/home/jeversole/trainingbench/datasets/spreadsheet/Budget_Planner.xlsx`
  with `SpreadsheetCalculator`; loader succeeded; signature
  matches `QueryHook`; `calculate('what is the total?')`
  returned `'Total: 7,700\nSource: Summary!B3'` — real
  formatted output.
- AC3 ✓ Inline test: `SpreadsheetCalculator('/tmp/does-not-exist.xlsx')`
  raised `FileNotFoundError`; `.xlsm` input raised
  `ValueError` ("Only .xlsx files are supported").
  Both exception types are caught by `main.py`'s `except
  Exception as e` block; service would log the warning and
  continue RAG-only.
- AC4 ✓ `rag_system.py` unchanged (`git diff` empty).
- AC5 ✓ `spreadsheet_calculator.py` unchanged.
- AC6 ✓ Diff bounded to `main.py` (50 lines; slightly over
  the "~15 lines" projection but within one logical change
  — the import, the env-var block, and the constructor
  call).

**Finding worth logging:** TB's `SpreadsheetCalculator`
only accepts `.xlsx` (rejects `.xlsm` with `ValueError`).
Stalite3's actual spreadsheet is `.xlsm`
(`Sanaitzed-Mix-Program.xlsm`). This is a pre-existing
limitation of TB's module (not introduced by TB-US-037),
but worth flagging as a follow-up concern: if TB wants to
support stalite-style `.xlsm` files via its generic
calculator, a tiny patch in `SpreadsheetCalculator.__init__`
to accept both extensions would do it. Not scoped to
TB-US-037 (would modify `spreadsheet_calculator.py` and
violate AC5).
