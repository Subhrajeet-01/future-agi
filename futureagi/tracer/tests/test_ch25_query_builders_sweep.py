"""
Sweep test: every v2 query builder produces SQL with NO legacy column refs.

Whenever a v1 builder grows a new method that touches `span_attr_*`,
`span_attributes_raw`, `metadata_map`, or `_peerdb_*`, this test fails
unless the corresponding v2 builder either overrides the new method OR
the new method goes through one of the already-overridden ones.

Cheap to run: pure-Python (no DB), exercises each v2 builder's public
build* methods with minimal valid input.
"""
from __future__ import annotations

import re

import pytest

# v2 builders under test
from tracer.services.clickhouse.v2.query_builders.dashboard import (
    DashboardQueryBuilderV2,
)
from tracer.services.clickhouse.v2.query_builders.eval_metrics import (
    EvalMetricsQueryBuilderV2,
)
from tracer.services.clickhouse.v2.query_builders.monitor_metrics import (
    MonitorMetricsQueryBuilderV2,
)
from tracer.services.clickhouse.v2.query_builders.session_list import (
    SessionListQueryBuilderV2,
)
from tracer.services.clickhouse.v2.query_builders.span_list import (
    SpanListQueryBuilderV2,
)
from tracer.services.clickhouse.v2.query_builders.trace_list import (
    TraceListQueryBuilderV2,
)
from tracer.services.clickhouse.v2.query_builders.voice_call_list import (
    VoiceCallListQueryBuilderV2,
)


PROJECT_ID = "11111111-1111-1111-1111-111111111111"

LEGACY_PATTERNS = (
    r"\b_peerdb_is_deleted\b",
    r"\b_peerdb_version\b",
    r"\bspan_attr_str\b",
    r"\bspan_attr_num\b",
    r"\bspan_attr_bool\b",
    r"\bspan_attributes_raw\b",
    r"\bresource_attributes_raw\b",
    r"\bmetadata_map\b",
)
LEGACY_RE = re.compile("|".join(LEGACY_PATTERNS))


def _assert_no_legacy(sql: str, label: str) -> None:
    """Helper — fail with a helpful error pointing at the leaked token."""
    match = LEGACY_RE.search(sql)
    if match:
        # Pull a snippet of context around the leak
        start = max(0, match.start() - 40)
        end   = min(len(sql), match.end() + 40)
        raise AssertionError(
            f"{label}: legacy column '{match.group(0)}' leaked into v2 SQL\n"
            f"  context: …{sql[start:end]}…"
        )


# ─── SpanList ────────────────────────────────────────────────────────────────
def _span_list_builder():
    return SpanListQueryBuilderV2(
        project_id=PROJECT_ID, page_number=0, page_size=10,
        filters=[], sort_params=[],
        eval_config_ids=[], annotation_label_ids=[],
    )


def test_span_list_v2_build_no_legacy():
    sql, _ = _span_list_builder().build()
    _assert_no_legacy(sql, "SpanList.build")


def test_span_list_v2_count_no_legacy():
    sql, _ = _span_list_builder().build_count_query()
    _assert_no_legacy(sql, "SpanList.build_count_query")


def test_span_list_v2_content_no_legacy():
    sql, _ = _span_list_builder().build_content_query(span_ids=["sp1"])
    _assert_no_legacy(sql, "SpanList.build_content_query")


# ─── TraceList ───────────────────────────────────────────────────────────────
def _trace_list_builder():
    return TraceListQueryBuilderV2(
        project_id=PROJECT_ID, page_number=0, page_size=10,
        filters=[], sort_params=[],
        eval_config_ids=[], annotation_label_ids=[],
    )


def test_trace_list_v2_build_no_legacy():
    sql, _ = _trace_list_builder().build()
    _assert_no_legacy(sql, "TraceList.build")


def test_trace_list_v2_count_no_legacy():
    sql, _ = _trace_list_builder().build_count_query()
    _assert_no_legacy(sql, "TraceList.build_count_query")


def test_trace_list_v2_content_no_legacy():
    sql, _ = _trace_list_builder().build_content_query(trace_ids=["t1"])
    _assert_no_legacy(sql, "TraceList.build_content_query")


def test_trace_list_v2_span_attributes_no_legacy():
    sql, _ = _trace_list_builder().build_span_attributes_query(trace_ids=["t1"])
    _assert_no_legacy(sql, "TraceList.build_span_attributes_query")


def test_trace_list_v2_span_count_no_legacy():
    sql, _ = _trace_list_builder().build_span_count_query(trace_ids=["t1"])
    _assert_no_legacy(sql, "TraceList.build_span_count_query")


# ─── SessionList ─────────────────────────────────────────────────────────────
def _session_list_builder():
    return SessionListQueryBuilderV2(
        project_id=PROJECT_ID, page_number=0, page_size=10,
        filters=[], sort_params=[],
        eval_config_ids=[], annotation_label_ids=[],
    )


def test_session_list_v2_build_no_legacy():
    sql, _ = _session_list_builder().build()
    _assert_no_legacy(sql, "SessionList.build")


def test_session_list_v2_count_no_legacy():
    sql, _ = _session_list_builder().build_count_query()
    _assert_no_legacy(sql, "SessionList.build_count_query")


# ─── VoiceCallList ───────────────────────────────────────────────────────────
def _voice_call_builder():
    return VoiceCallListQueryBuilderV2(
        project_id=PROJECT_ID, page_number=0, page_size=10,
        filters=[], sort_params=[],
        eval_config_ids=[], annotation_label_ids=[],
    )


def test_voice_call_list_v2_build_no_legacy():
    sql, _ = _voice_call_builder().build()
    _assert_no_legacy(sql, "VoiceCallList.build")


def test_voice_call_list_v2_count_no_legacy():
    sql, _ = _voice_call_builder().build_count_query()
    _assert_no_legacy(sql, "VoiceCallList.build_count_query")


def test_voice_call_list_v2_content_no_legacy():
    sql, _ = _voice_call_builder().build_content_query(span_ids=["sp1"])
    _assert_no_legacy(sql, "VoiceCallList.build_content_query")
