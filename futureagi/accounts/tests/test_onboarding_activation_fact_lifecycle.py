import io
import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.models import (
    OnboardingActivationFactReceipt,
    OnboardingLifecycleEvaluationLog,
)
from accounts.services.onboarding.activation_exporter import (
    ACTIVATION_EXPORT_SCHEMA_VERSION,
)
from accounts.services.onboarding.activation_fact_lifecycle import (
    import_activation_fact_lifecycle_evaluations,
)
from accounts.services.onboarding.lifecycle_sender import (
    send_limited_onboarding_lifecycle_batch,
)


def _receipt(organization, workspace, user, **overrides):
    now = overrides.pop("evaluated_at", timezone.now())
    fields = {
        "export_log_id": uuid.uuid4(),
        "idempotency_key": f"{workspace.id}:activation:{uuid.uuid4()}",
        "schema_version": ACTIVATION_EXPORT_SCHEMA_VERSION,
        "event_cursor": now.isoformat(),
        "organization_id_value": organization.id,
        "workspace_id_value": workspace.id,
        "user_id_value": user.id,
        "deployment_mode": "cloud",
        "deployment_region": "us",
        "plan_tier": "payg",
        "activation_stage": "waiting_for_first_trace",
        "primary_path": "observe",
        "is_activated": False,
        "lifecycle_campaign_key": "observe_waiting_for_first_trace",
        "lifecycle_template_key": "observe_waiting_for_first_trace_v1",
        "lifecycle_status": OnboardingLifecycleEvaluationLog.STATUS_ELIGIBLE,
        "email_next_key": "observe_waiting_for_first_trace_v1",
        "email_eligible": True,
        "email_suppressed": False,
        "journey_config_schema_version": "onboarding-activation-export-config-2026-05-30.v1",
        "primary_cohort_key": "observe_waiting_first_trace",
        "cohort_keys": ["observe_waiting_first_trace"],
        "journey_cohorts": [
            {
                "cohort_key": "observe_waiting_first_trace",
                "target_action_id": "send_first_trace",
                "target_success_event": "trace_received",
                "priority": 95,
            }
        ],
        "payload_hash": "a" * 64,
        "payload": {
            "fact": {
                "activation": {
                    "stage": "waiting_for_first_trace",
                    "primary_path": "observe",
                    "is_activated": False,
                }
            }
        },
        "evaluated_at": now,
        "metadata": {"source": "activation_fact_receiver"},
    }
    fields.update(overrides)
    return OnboardingActivationFactReceipt.no_workspace_objects.create(**fields)


@pytest.mark.django_db
def test_activation_fact_lifecycle_import_writes_eligible_log(
    organization,
    workspace,
    user,
):
    receipt = _receipt(organization, workspace, user)

    result = import_activation_fact_lifecycle_evaluations(limit=10)

    assert result.evaluated == 1
    assert result.imported == 1
    assert result.status_counts == {"imported": 1}
    log = OnboardingLifecycleEvaluationLog.no_workspace_objects.get()
    assert log.source_receipt == receipt
    assert log.status == OnboardingLifecycleEvaluationLog.STATUS_ELIGIBLE
    assert log.campaign_key == "observe_waiting_for_first_trace"
    assert log.template_key == "observe_waiting_for_first_trace_v1"
    assert log.activation_stage == "waiting_for_first_trace"
    assert log.primary_path == "observe"
    assert log.target_action_id == "send_first_trace"
    assert log.target_success_event == "trace_received"
    assert log.target_url is None
    assert log.eligible_at == receipt.evaluated_at
    assert log.metadata["source"] == "activation_fact_receipt"
    assert log.metadata["send_enabled"] is False
    assert log.metadata["receipt_id"] == str(receipt.id)
    assert log.metadata["cohort_keys"] == ["observe_waiting_first_trace"]


@pytest.mark.django_db
def test_activation_fact_lifecycle_import_is_idempotent(
    organization,
    workspace,
    user,
):
    _receipt(organization, workspace, user)

    first = import_activation_fact_lifecycle_evaluations(limit=10)
    second = import_activation_fact_lifecycle_evaluations(limit=10)

    assert first.imported == 1
    assert second.evaluated == 0
    assert second.imported == 0
    assert OnboardingLifecycleEvaluationLog.no_workspace_objects.count() == 1


@pytest.mark.django_db
def test_activation_fact_lifecycle_import_skips_duplicate_campaign_candidate(
    organization,
    workspace,
    user,
):
    _receipt(organization, workspace, user)
    _receipt(organization, workspace, user)

    result = import_activation_fact_lifecycle_evaluations(limit=10)

    assert result.evaluated == 2
    assert result.imported == 1
    assert result.status_counts == {"imported": 1, "skipped": 1}
    assert result.skip_counts == {"existing_lifecycle_candidate": 1}
    assert OnboardingLifecycleEvaluationLog.no_workspace_objects.count() == 1


@pytest.mark.django_db
def test_activation_fact_lifecycle_import_filters_non_paid_cloud_receipts(
    organization,
    workspace,
    user,
):
    _receipt(organization, workspace, user, deployment_mode="self_hosted")
    _receipt(organization, workspace, user, plan_tier="free")
    _receipt(organization, workspace, user, email_suppressed=True)
    _receipt(
        organization,
        workspace,
        user,
        lifecycle_status=OnboardingLifecycleEvaluationLog.STATUS_SUPPRESSED,
    )

    result = import_activation_fact_lifecycle_evaluations(limit=10)

    assert result.evaluated == 0
    assert result.imported == 0
    assert OnboardingLifecycleEvaluationLog.no_workspace_objects.count() == 0


@pytest.mark.django_db
def test_activation_fact_lifecycle_import_skips_unresolved_user(
    organization,
    workspace,
    user,
):
    _receipt(organization, workspace, user, user_id_value=uuid.uuid4())

    result = import_activation_fact_lifecycle_evaluations(limit=10)

    assert result.evaluated == 1
    assert result.imported == 0
    assert result.status_counts == {"skipped": 1}
    assert result.skip_counts == {"missing_user": 1}
    assert OnboardingLifecycleEvaluationLog.no_workspace_objects.count() == 0


@pytest.mark.django_db
def test_activation_fact_lifecycle_import_skips_unknown_campaign(
    organization,
    workspace,
    user,
):
    _receipt(organization, workspace, user, lifecycle_campaign_key="unknown_campaign")

    result = import_activation_fact_lifecycle_evaluations(limit=10)

    assert result.evaluated == 1
    assert result.imported == 0
    assert result.status_counts == {"skipped": 1}
    assert result.skip_counts == {"unknown_campaign": 1}
    assert OnboardingLifecycleEvaluationLog.no_workspace_objects.count() == 0


@pytest.mark.django_db
def test_activation_fact_lifecycle_import_supports_command_no_write(
    organization,
    workspace,
    user,
):
    _receipt(organization, workspace, user)
    stdout = io.StringIO()

    call_command(
        "run_onboarding_activation_fact_lifecycle_import",
        "--limit",
        "10",
        "--no-write",
        stdout=stdout,
    )

    output = stdout.getvalue()
    assert "evaluated=1" in output
    assert "imported=0" in output
    assert "status_counts={'would_import': 1}" in output
    assert OnboardingLifecycleEvaluationLog.no_workspace_objects.count() == 0


@pytest.mark.django_db
def test_receipt_sourced_lifecycle_logs_are_excluded_from_send_batch(
    organization,
    workspace,
    user,
):
    _receipt(organization, workspace, user)
    import_activation_fact_lifecycle_evaluations(limit=10)

    result = send_limited_onboarding_lifecycle_batch(
        cohort="internal",
        limit=10,
        dry_run=True,
    )

    assert result.evaluated == 0
    assert result.sent == 0
    assert result.candidates == ()
