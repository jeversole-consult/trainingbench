# TB-US-025: Quantitative handler — deterministic calculator framework

**Status**: In Progress
**Created**: 2026-10-14
**Author**: Jesse Eversole
**Commit hash(es)**: <filled in on completion>

## Story

As the operator of an OT-equipped TrainingBench agent, I want a
**quantitative handler** that routes classified prompts to
deterministic calculators (plain code, no LLM), so that the
system gets arithmetic and formula-based computation right
every time instead of asking an LLM to guess at math.

## Background

Per the OT context doc, the quantitative handler owns prompts
that require **calculation using known formulas or
deterministic computation**. Example patterns:
`"how much..."`, `"calculate..."`, `"what's the total..."`.
The handler is **deterministic code** — not an LLM — because
calculators get arithmetic right while LLMs famously don't.

v0.1 ships a **framework** for registering domain calculators
and at least one concrete calculator wired up (math_basic) so
the architecture is proven by use. Domain-specific calculators
(medical dosage math, legal fee calculations, agricultural
yield formulas) get their own stories as domains come online.

## Requirements

### Framework

- [ ] R1: **Calculator registry.** A module
      `backend/api/handlers/quantitative.py` exposes a
      registry pattern:
      ```python
      CALCULATORS: Dict[str, Calculator] = {}

      def register(name: str) -> Callable:
          # decorator or direct call registers a Calculator subclass

      class Calculator(Protocol):
          def extract_parameters(self, prompt: str) -> Dict
          def compute(self, params: Dict) -> Any
          def format(self, result: Any, params: Dict) -> str
      ```
- [ ] R2: **Handler entry point.** Function
      `handle_quantitative(prompt: str, audit_entry: dict) ->
      str` that:
      1. Selects the appropriate calculator (v0.1 heuristic:
         try each registered calculator's `extract_parameters`;
         first one that returns non-null wins; dispatch deepens
         in v0.2+).
      2. Calls `compute(params)`.
      3. Calls `format(result, params)`.
      4. Logs handler details to the audit entry via TB-US-024's
         `add_handler()` interface.
      5. Returns the formatted string response.
- [ ] R3: **At least one concrete calculator** registered at
      v0.1: `math_basic` — handles simple arithmetic in
      prompts like `"what is 2 + 2"`, `"calculate 15% of 240"`,
      `"how much is 3 * 4 - 7"`. Pattern matching + Python
      `eval` restricted to safe arithmetic ops is acceptable
      for v0.1 (uses `ast.parse` + whitelist of operator
      nodes, not raw eval — see Design Notes).
- [ ] R4: **No-calculator-matched case.** If no registered
      calculator can extract parameters, return a clear error
      response: `"No calculator was able to handle this
      quantitative prompt."` Log `handler.success = false`
      and `handler.error = "no_calculator_matched"`.
- [ ] R5: **Error handling.** Any exception raised by a
      calculator (division by zero, overflow, parse error)
      is caught, logged in the audit entry
      (`handler.success = false`,
      `handler.error = <exception message>`), and returned to
      the caller as a user-safe error message.

### Programmatic + HTTP

- [ ] R6: **`handle_quantitative()`** is the primary
      interface; called by the OT router (TB-US-028). An HTTP
      endpoint `POST /ot/handle/quantitative` is **not
      required** in v0.1 — the handler is invoked through
      the router, not directly. (If a direct debug/test
      endpoint is desired, implementer may add it; mark it
      super-user-only.)

### Role gating

- [ ] R7: **Pure function, no role check.** The handler
      itself does not enforce roles — the OT router
      (TB-US-028) is the role-check surface. Any
      authenticated user whose request reaches this handler
      is allowed to use it.

## Acceptance Criteria

- [ ] AC1: Calling `handle_quantitative("what is 2 + 2",
      audit_entry={})` returns `"4"` (or a formatted
      equivalent). The audit entry has
      `handler.name = "quantitative"`,
      `handler.calculator = "math_basic"`,
      `handler.success = true`.
- [ ] AC2: Calling with `"calculate 15% of 240"` returns
      `"36"` (or a formatted equivalent).
- [ ] AC3: Calling with a prompt that no calculator can
      handle (e.g. `"what should I eat for dinner"`) returns
      the "no calculator matched" error with
      `handler.success = false`.
- [ ] AC4: A calculator that raises during `compute()` (e.g.,
      division by zero) results in a user-safe error response;
      the audit entry captures the exception message in
      `handler.error`.
- [ ] AC5: Registering a new calculator via the registry
      works without modifying the handler's dispatch code —
      the registry is the source of truth.
- [ ] AC6: `handle_quantitative()` is importable and callable
      from the router (TB-US-028) without going through HTTP.
- [ ] AC7: No LLM is called during any quantitative-handler
      path. Verified by code inspection and absence of model
      inference time in the handler's latency measurement.

## Design Notes

- **`eval` is not used; AST-based safe evaluation is.** Python's
  `ast.parse` + a whitelist of allowed node types
  (`BinOp`, `Num`, `Constant`, specific operators `Add`, `Sub`,
  `Mult`, `Div`, `Mod`, `Pow`, `USub`, `UAdd`) gives safe
  arithmetic evaluation without the security problems of raw
  `eval`. This is a standard pattern.
- **Why dispatch is "try each calculator" in v0.1.** At one
  calculator, there's no dispatch problem. At five
  calculators, it's O(n) extraction attempts per prompt —
  still fine. At fifty, a smarter dispatch (either
  pattern-matched or classified-by-sub-type) is wanted —
  separate story in a later version.
- **Why no HTTP endpoint for direct handler call.** The OT
  pipeline is: classify → route → handle. Direct handler
  invocation would skip classification + audit, which
  defeats the point of OT. Debug access can go through
  `/ot/classify` + manual dispatch during development.
- **Parameter extraction is the hardest part.** For
  `math_basic`, extract: find the arithmetic expression in
  the prompt and evaluate it. For a dosage calculator,
  extract: weight, drug, concentration. Each calculator
  owns its own extraction logic — that is the price of
  determinism.
- **Return value is a string.** Handlers return formatted
  strings suitable for user display. If a future need wants
  machine-readable responses (dict, number), that is a
  separate concern (and probably belongs in a different
  endpoint, not the OT router).
- **Audit entry mutation.** The handler mutates the passed-in
  `audit_entry` dict rather than returning additional
  metadata. This matches the pattern TB-US-024's audit module
  provides (`start_entry` → `add_classification` →
  `add_handler` → `finalize`).

## Out of Scope

- **Specific domain calculators** beyond `math_basic`.
  Medical dosage, legal fee, agricultural yield, etc. — each
  is a separate v0.1-or-later story once the domain comes
  online.
- **Natural-language-to-formula translation** for complex
  prompts. v0.1 handles arithmetic in a prompt via pattern
  extraction; it does not solve word problems.
- **Multi-step computations** (chain multiple calculators).
  v0.1 handles one-shot computation per prompt. Chaining is
  v0.2+ or belongs in the mixed handler (TB-US-027).
- **Streaming responses** / incremental computation. v0.1
  handlers are synchronous and return a complete response.
- **Calculator-specific authentication / per-calculator
  permissions.** All registered calculators are usable by
  anyone whose request reaches the quantitative handler.
- **A/B calculator comparison** (two calculators proposing
  answers to the same prompt). Separate story if ever
  useful.
- **Direct-invocation HTTP endpoint.** Flagged as optional
  (R6); not required.
- **Branding tweaks.**

## Related

- Parent: [TB-US-022](tb-us-022.md) — OT coordinator.
- Called by: [TB-US-028](tb-us-028.md) — OT router dispatches
  classified-quantitative prompts here.
- Logs to: [TB-US-024](tb-us-024.md) — audit module.
- Verified by: [TB-US-029](tb-us-029.md) — the math example
  exercises this handler with real quantitative queries.
- Context: `docs/ot-context-for-claude-code_1.md` lines 29–31
  (category description), 80–83 (handler description).
- Sibling handlers (same layer): [TB-US-026](tb-us-026.md)
  (lookup), [TB-US-027](tb-us-027.md) (mixed),
  [TB-US-028](tb-us-028.md) (qualitative via OT routing).
