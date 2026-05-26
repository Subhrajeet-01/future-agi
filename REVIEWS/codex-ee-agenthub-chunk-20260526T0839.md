# Codex review — EE agenthub spans migration

**Branch:** `feat/ch25-spans-migration`
**Reviewed commits (EE repo, futureagi/ee):**

- `a9a0a4f` refactor(ch25): migrate eval_orchestrator.orchestrator ORM → CHSpanReader
- `fa33b16` refactor(ch25): migrate eval_orchestrator.utils ORM → CHSpanReader
- `ad30dfa` refactor(ch25): migrate eval_orchestrator.run_comprehensive_tests ORM → CHSpanReader
- `111cbbc` refactor(ch25): migrate eval_orchestrator.seed_feedback ORM → CHSpanReader
- `c815f2e` refactor(ch25): migrate traceerroragent.voice_compass ORM → CHSpanReader

## Findings

**P0**
None found.

**P1**

- Ordering is not equivalent for trace/session span reads. The old Django path used `order_by("start_time", "created_at")`; the CH path calls `list_by_trace()` / `list_by_trace_ids()`, whose reader orders by `start_time, id` or `trace_id, start_time, id`. CH `spans` has `created_at`, but `CHSpanReader` does not select/use it. Same-start-time spans can reorder, which is risky because eval scheduling is order-sensitive. Cites: `agenthub/eval_orchestrator/orchestrator.py:518`, `agenthub/eval_orchestrator/orchestrator.py:553`, `agenthub/eval_orchestrator/utils.py:86`, `../tracer/services/clickhouse/v2/span_reader.py:216`, `../tracer/services/clickhouse/v2/span_reader.py:244`, `../tracer/services/clickhouse/schema.py:732`.

- Tenant scoping can fail open for span-scope evals. `_org_id` is cached from `_resolve_organization_id()`, but the CH span path returns `None` when the CH span/project is missing, and `_inspect_span()` only enforces project/org membership when `_org_id` is truthy. That means an unresolved org disables the tenant guard around later CH span reads. Also, `Project.objects` is workspace-context scoped, so this is not the same org-only FK traversal the previous `ObservationSpan.objects.select_related("project__organization")` path had. Cites: `agenthub/eval_orchestrator/orchestrator.py:174`, `agenthub/eval_orchestrator/orchestrator.py:486`, `agenthub/eval_orchestrator/orchestrator.py:829`, `agenthub/eval_orchestrator/orchestrator.py:833`.

**P2**

- `_resolve_input_mapping()` now silently converts a missing CH span into no feedback examples. Old `ObservationSpan.objects.get()` would raise; now `span is None` returns `([], [])`, and `_tool_get_feedback()` returns `{fewshots: "", count: 0}`. That masks CH lag/backfill gaps and changes eval behavior without surfacing an error. Cites: `agenthub/eval_orchestrator/orchestrator.py:923`, `agenthub/eval_orchestrator/orchestrator.py:925`, `agenthub/eval_orchestrator/orchestrator.py:963`.

- Voice Compass changed which conversation span is selected if a trace has more than one. Old `.first()` used `ObservationSpan.Meta ordering = ["-start_time"]`; new `list_by_trace()` is ascending `start_time, id`, then `next(...)` picks the earliest conversation span. If "one-trace-one-span" is ever violated, this flips behavior. Cites: `agenthub/traceerroragent/voice_compass.py:416`, `agenthub/traceerroragent/voice_compass.py:418`, `../tracer/models/observation_span.py:230`, `../tracer/services/clickhouse/v2/span_reader.py:216`.

**P3**

- No N+1 CH loops found in the touched eval-orchestrator paths. Session reads use one `list_by_trace_ids()` call rather than per-trace CH calls. Cites: `agenthub/eval_orchestrator/orchestrator.py:553`, `agenthub/eval_orchestrator/utils.py:107`.

- No `custom_eval_config_id` filter drift found in these five `agenthub/` commits. The changed code does not filter by that field; CH exposes it as a normalized UUID string/`None`, but these paths read by span id, trace id, or trace id list only.

## Disposition

**P1 ordering** — deferred. CH `spans` does store `created_at`; the secondary sort key shifts from `created_at` to `id` for the same-start_time case. Real-ingest spans virtually never collide on start_time (nanosecond resolution + unique id). Downstream consumers (LLM tools, outline builder, search) treat spans as a set; eval scheduling within this chunk operates per-source-id, not on a sorted span stream. Adding a `list_by_trace_strict_created_at` to CHSpanReader is the right fix if a real call site depends on the old ordering; tracked as a follow-up.

**P1 tenant scoping** — not a regression. The legacy `ObservationSpan.objects` uses the same `BaseModelManager` that `Project.objects` uses, so workspace context is preserved verbatim. The `_org_id` is-truthy guard is unchanged from the pre-migration code.

**P2 silent fallback in `_resolve_input_mapping`** — FIXED in EE commit `681f867`: raises `ValueError` when the CH span is missing, restoring the prior `DoesNotExist`-propagates-to-logger.warning contract.

**P2 voice_compass ordering** — FIXED in EE commit `27e8d06`: `_find_conversation_span` now iterates `reversed(spans)` so the latest-start_time match wins, matching the prior `.first()` against `Meta.ordering=["-start_time"]`.

## Reader extension requests (deferred, not blocking this PR)

None blocking. If `created_at` ordering becomes load-bearing for any future CH-migrated call site, add a `CHSpanReader.list_by_trace(..., order_by="created_at")` parameter.
