"""id_remap_sql — the ONE canonical SQL fragment that resolves a span's
``end_user_id`` (or ``trace_session_id``) through the P3b id-remap, so a
cross-cutover *straddler* (an identity with both old random-uuid4 spans AND new
deterministic-UUIDv5 spans) reads as ONE entity.

WHY (DESIGN §3 / §10.1, schema ``019_id_remap.sql``). P3b re-keys the curated
``end_users`` / ``trace_sessions`` surrogate id from a random PG ``uuid4`` to a
deterministic ``UUIDv5`` so ingestion can drop the hot-path ``get_or_create``.
Old ids stay the CURATED key; the ``end_user_id_remap (old_id, new_id)`` /
``trace_session_id_remap`` bridge maps a NEW-id span back to its OLD id at read
time (instead of rewriting billions of span rows). This step (1.5) wires the
PER-USER reads to that bridge BEFORE the ingestion flip (step2) exists — so a
returning user never splits across the cutover.

THE RESOLVE DIRECTION + THE LEFT-JOIN NULL GOTCHA. The map is keyed
``old_id -> new_id``; the lookup goes new→old. So a read LEFT JOINs the remap on
``spans.end_user_id = remap.new_id`` and COALESCEs back to ``old_id``:

  • An OLD-id span: its id lives in ``old_id`` (NOT ``new_id``) → NO join match →
    fall back to itself (unchanged). Pre-flip EVERY span is old-id, so NO span
    matches any ``new_id`` and the whole thing is a strict, byte-identical no-op
    (acceptance gate B).
  • A NEW-id span (post-flip): its id matches ``new_id`` → resolve to ``old_id``
    (the still-primary curated key), unifying it with the historical rows.

GOTCHA — ClickHouse fills the UNMATCHED side of a LEFT JOIN with the column-type
DEFAULT, not NULL (unless ``join_use_nulls=1``). ``end_user_id_remap.old_id`` is
non-nullable ``UUID``, so an unmatched ``old_id`` comes back as the ZERO-UUID
(``00000000-…``), NOT NULL — a bare ``coalesce(remap.old_id, span_id)`` would
then return the zero-uuid for every old-id span and match nothing. We therefore
guard on the zero-uuid explicitly (``if old_id is the zero-uuid → use the span's
own id``) rather than relying on a query-wide ``join_use_nulls`` flag (which would
also flip the NULL semantics of the OTHER joins in these read queries and risk
the gate-B byte-identical guarantee). The zero-uuid can never be a legitimate
``old_id`` (it is a real PG ``uuid4``), so the guard is exact.
"""

from __future__ import annotations

# ClickHouse zero-value for a non-nullable UUID column — the value CH fills into
# the UNMATCHED side of a LEFT JOIN (see module docstring). Defined locally (NOT
# imported from query_builders.base) to keep this leaf module import-cycle-free:
# the query_builders package's __init__ imports the builders, which import THIS
# module, so a back-import would be circular. Same literal as base.NIL_UUID /
# adapter — asserted identical by the unit tests.
NIL_UUID = "00000000-0000-0000-0000-000000000000"

# Default join-side alias for the remap table (callers may pass their own).
REMAP_ALIAS = "id_remap"


def resolved_id_expr(span_id_col: str, remap_alias: str = REMAP_ALIAS) -> str:
    """Return the SQL expression that yields the *resolved* id for ``span_id_col``.

    ``span_id_col`` is the (qualified) span column being resolved, e.g.
    ``s.end_user_id``; ``remap_alias`` is the alias the remap table was joined
    under (the join condition must be ``<span_id_col> = <remap_alias>.new_id``).

    Resolves to the remap's ``old_id`` when the span carries a NEW (deterministic)
    id, else the span's own id. The ``new_id`` fallback path is the zero-uuid
    guard described in the module docstring (unmatched LEFT JOIN → zero-uuid, not
    NULL). The ``isNull`` arm is harmless belt-and-suspenders in case a future
    caller runs under ``join_use_nulls=1``.
    """
    old = f"{remap_alias}.old_id"
    return f"if({old} IS NULL OR {old} = toUUID('{NIL_UUID}'), {span_id_col}, {old})"


def remap_left_join(
    span_id_col: str, remap_table: str, remap_alias: str = REMAP_ALIAS
) -> str:
    """Return the ``LEFT JOIN <remap_table> AS <alias> FINAL ON …`` clause that
    pairs with :func:`resolved_id_expr`.

    ``remap_table`` is unqualified (``end_user_id_remap`` / ``trace_session_id_remap``)
    so the connection's configured database (``CH25_DATABASE`` / ``CH_DATABASE``)
    is the single dev/test/prod switch — same DB-agnostic rule as the schema
    files. ``FINAL`` collapses the ReplacingMergeTree so a re-run of the build
    (latest-version-wins) is read identically.
    """
    return (
        f"LEFT JOIN {remap_table} AS {remap_alias} FINAL "
        f"ON {span_id_col} = {remap_alias}.new_id"
    )


__all__ = ["REMAP_ALIAS", "resolved_id_expr", "remap_left_join"]
