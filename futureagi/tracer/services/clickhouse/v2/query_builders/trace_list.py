"""
v2 TraceList query builder — targets the CH 25.3 spans schema.

Same pattern as v2/span_list.py: SUBCLASS the v1 builder, rewrite the
compiled SQL output. The v1 TraceList builder reads from `spans` (legacy
24.10 columns) plus joins to `tracer_eval_logger` and `model_hub_score`.
We rewrite the `spans` table references; eval and annotation joins are
unchanged.

Methods overridden:
  - `build()` — Phase 1: light trace+root-span page (no input/output)
  - `build_content_query()` — Phase 2: heavy span_attr maps + metadata_map
  - `build_span_attributes_query()` — Phase 3: span_attributes_raw fetch
  - `build_count_query()` — pagination count
  - `build_span_count_query()` — per-trace span tally
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from tracer.services.clickhouse.query_builders.trace_list import TraceListQueryBuilder
from tracer.services.clickhouse.v2.query_builders.filters import rewrite_v1_sql_to_v2


class TraceListQueryBuilderV2(TraceListQueryBuilder):
    """Drop-in v2 TraceList builder.

    Callers swap one import line:
        v1: from tracer.services.clickhouse.query_builders.trace_list import TraceListQueryBuilder
        v2: from tracer.services.clickhouse.v2.query_builders.trace_list  import TraceListQueryBuilderV2

    Or route via the shadow harness in v2/shadow.py.
    """

    def build(self) -> Tuple[str, Dict[str, Any]]:
        sql, params = super().build()
        return rewrite_v1_sql_to_v2(sql), params

    def build_content_query(self, trace_ids: List[str]) -> Tuple[str, Dict[str, Any]]:
        sql, params = super().build_content_query(trace_ids)
        return rewrite_v1_sql_to_v2(sql), params

    def build_span_attributes_query(self, *args, **kwargs) -> Tuple[str, Dict[str, Any]]:
        sql, params = super().build_span_attributes_query(*args, **kwargs)
        return rewrite_v1_sql_to_v2(sql), params

    def build_count_query(self) -> Tuple[str, Dict[str, Any]]:
        sql, params = super().build_count_query()
        return rewrite_v1_sql_to_v2(sql), params

    def build_span_count_query(self, *args, **kwargs) -> Tuple[str, Dict[str, Any]]:
        sql, params = super().build_span_count_query(*args, **kwargs)
        return rewrite_v1_sql_to_v2(sql), params


__all__ = ["TraceListQueryBuilderV2"]
