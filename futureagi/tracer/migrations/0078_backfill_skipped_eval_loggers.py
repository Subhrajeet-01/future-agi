"""TH-4910: backfill legacy "Required attribute" rows to the skipped sentinel.

Before this PR, when ``_process_mapping`` raised because a span lacked
the attribute its eval mapping pointed at, the dispatch wrote an
``EvalLogger`` row with ``error=True`` and ``error_message`` starting
with "Error during evaluation: Required attribute". The dashboard then
rendered "Fail" / "Error" — the bug Mudflap / Ghosted-Prod filed.

The new code branches on ``EvalSkippedMissingAttribute`` and writes
the row with the sentinel ``output_str = "__SKIPPED_MISSING_ATTRIBUTE__"``,
``error=False``, ``error_message=NULL`` so the read paths render it as
"Skipped".

Existing rows from before this PR still have the legacy shape. This
migration rewrites them to the new shape in a single UPDATE so customer
dashboards reflect the fix without waiting for the eval task to re-run.

Forward-only — the rewrite clears ``error_message``, so reverse can't
reconstruct which rows were the originals.
"""

from django.db import migrations


# Inlined (rather than imported from tracer.utils.eval) so the migration
# is stable even if the constant is renamed later. Migrations are
# historical artefacts; they shouldn't depend on the live module.
LEGACY_ERROR_PREFIX = "Error during evaluation: Required attribute"
SKIPPED_OUTPUT_STR = "__SKIPPED_MISSING_ATTRIBUTE__"


def forward(apps, schema_editor):
    EvalLogger = apps.get_model("tracer", "EvalLogger")
    EvalLogger.objects.filter(
        error=True,
        error_message__startswith=LEGACY_ERROR_PREFIX,
    ).update(
        error=False,
        error_message=None,
        output_str=SKIPPED_OUTPUT_STR,
    )


def reverse(apps, schema_editor):
    """No-op — the rewrite cleared ``error_message`` so reverse is lossy."""
    return


class Migration(migrations.Migration):
    dependencies = [
        ("tracer", "0077_merge_20260514_1559"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
