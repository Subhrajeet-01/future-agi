from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.services.onboarding.activation_events import record_event
from accounts.services.onboarding.activation_state import resolve_activation_state
from accounts.services.onboarding.context import OnboardingContext
from accounts.services.onboarding.signal_resolver import collect_onboarding_signals
from accounts.tests.onboarding_model_factories import (
    create_custom_eval,
    create_observe_project,
    create_trace,
)


def _flags(**overrides):
    flags = {
        "onboarding_activation_state_api": True,
        "onboarding_goal_picker": True,
        "onboarding_path_cards": True,
        "onboarding_sample_project": False,
        "onboarding_daily_quality_home": True,
        "onboarding_lifecycle_email_dry_run": True,
        "onboarding_email_welcome_enabled": False,
        "onboarding_email_first_action_recovery_enabled": False,
        "onboarding_email_first_signal_enabled": False,
        "onboarding_email_next_loop_enabled": False,
        "onboarding_email_sample_bridge_enabled": False,
        "onboarding_email_daily_digest_enabled": True,
        "onboarding_home_enabled": True,
        "onboarding_observe_mvp_enabled": True,
        "onboarding_sample_project_enabled": False,
        "onboarding_lifecycle_dry_run_enabled": True,
        "onboarding_lifecycle_send_enabled": False,
        "daily_quality_home_enabled": True,
        "activation_state_debug_enabled": False,
    }
    flags.update(overrides)
    return flags


def _context(user, organization, workspace, *, can_write=True):
    return OnboardingContext(
        user=user,
        organization=organization,
        workspace=workspace,
        organization_role="Owner" if can_write else "Viewer",
        workspace_role="workspace_admin" if can_write else "workspace_viewer",
        organization_level=15 if can_write else 1,
        workspace_level=8 if can_write else 1,
        selected_goal="monitor_production_ai_app",
        primary_path="observe",
        persona="developer",
        source="test",
        email_context=None,
        permissions={
            "role": "Owner" if can_write else "Viewer",
            "can_read": True,
            "can_write": can_write,
            "can_manage_workspace": can_write,
            "missing_permissions": [] if can_write else ["workspace:write"],
            "request_access_href": "/dashboard/settings/user-management",
            "permission_limited": not can_write,
        },
        warnings=[],
    )


def _set_created_at(instance, value):
    type(instance).no_workspace_objects.filter(id=instance.id).update(created_at=value)
    instance.refresh_from_db()


def _activated_observe_workspace(organization, workspace, user, *, now):
    project = create_observe_project(
        organization=organization,
        workspace=workspace,
        user=user,
    )
    trace = create_trace(project=project)
    _set_created_at(trace, now - timedelta(hours=3))
    create_custom_eval(organization=organization, workspace=workspace, project=project)
    record_event(
        user=user,
        organization=organization,
        workspace=workspace,
        event_name="trace_reviewed",
        source="test",
        product_path="observe",
        occurred_at=now - timedelta(hours=2, minutes=30),
    )
    record_event(
        user=user,
        organization=organization,
        workspace=workspace,
        event_name="first_quality_loop_completed",
        source="test",
        product_path="observe",
        occurred_at=now - timedelta(hours=2),
    )
    return project


def _activation_state(user, organization, workspace, *, flags=None, can_write=True):
    return resolve_activation_state(
        context=_context(user, organization, workspace, can_write=can_write),
        flags=flags or _flags(),
        signals=collect_onboarding_signals(
            user=user,
            organization=organization,
            workspace=workspace,
        ),
    )


@pytest.mark.django_db
def test_daily_quality_promotes_new_failed_trace_to_primary_signal(
    organization,
    workspace,
    user,
):
    now = timezone.now()
    project = _activated_observe_workspace(organization, workspace, user, now=now)
    failed_trace = create_trace(project=project, error={"type": "provider_error"})
    _set_created_at(failed_trace, now - timedelta(minutes=15))

    payload = _activation_state(user, organization, workspace)

    daily_quality = payload["daily_quality"]
    assert payload["stage"] == "daily_review"
    assert payload["home_mode"] == "daily_quality"
    assert daily_quality["mode"] == "new_signal"
    assert daily_quality["top_signal"]["type"] == "trace_failure"
    assert daily_quality["top_signal"]["is_sample"] is False
    assert payload["recommended_action"]["id"] == "review_failed_trace"
    assert payload["recommended_action"]["href"] == daily_quality["top_signal"]["route"]
    assert payload["email_eligibility"]["digest_eligible"] is True


@pytest.mark.django_db
def test_daily_quality_no_signal_returns_constructive_action_without_digest(
    organization,
    workspace,
    user,
):
    now = timezone.now()
    _activated_observe_workspace(organization, workspace, user, now=now)

    payload = _activation_state(user, organization, workspace)

    daily_quality = payload["daily_quality"]
    assert daily_quality["mode"] == "no_new_signal"
    assert daily_quality["top_signal"] is None
    assert daily_quality["primary_action"]["id"] == "create_trace_alert"
    assert daily_quality["digest_eligible"] is False
    assert daily_quality["digest_suppression_reason"] == "no_useful_signal"
    assert payload["email_eligibility"]["eligible"] is False
    assert payload["email_eligibility"]["suppression_reason"] == "no_useful_signal"


@pytest.mark.django_db
def test_daily_quality_uses_last_review_to_hide_already_reviewed_signal(
    organization,
    workspace,
    user,
):
    now = timezone.now()
    project = _activated_observe_workspace(organization, workspace, user, now=now)
    failed_trace = create_trace(project=project, error={"type": "provider_error"})
    _set_created_at(failed_trace, now - timedelta(minutes=30))
    record_event(
        user=user,
        organization=organization,
        workspace=workspace,
        event_name="daily_quality_item_reviewed",
        source="test",
        product_path="observe",
        metadata={
            "signal_id": f"trace_failure:{failed_trace.id}",
            "signal_type": "trace_failure",
            "source_type": "trace",
            "source_id": str(failed_trace.id),
            "project_id": str(project.id),
        },
        occurred_at=now - timedelta(minutes=5),
    )

    payload = _activation_state(user, organization, workspace)

    assert payload["daily_quality"]["mode"] == "no_new_signal"
    assert payload["daily_quality"]["top_signal"] is None


@pytest.mark.django_db
def test_sample_only_activity_never_enters_daily_quality(
    organization,
    workspace,
    user,
):
    now = timezone.now()
    project = create_observe_project(
        organization=organization,
        workspace=workspace,
        user=user,
        metadata={"is_sample": True},
    )
    create_trace(project=project, metadata={"is_sample": True})
    record_event(
        user=user,
        organization=organization,
        workspace=workspace,
        event_name="first_quality_loop_completed",
        source="sample",
        product_path="observe",
        is_sample=True,
        occurred_at=now - timedelta(hours=1),
    )

    payload = _activation_state(user, organization, workspace)

    assert payload["stage"] == "connect_observability"
    assert "daily_quality" not in payload


@pytest.mark.django_db
def test_permission_limited_daily_quality_routes_to_request_access(
    organization,
    workspace,
    user,
):
    now = timezone.now()
    _activated_observe_workspace(organization, workspace, user, now=now)

    payload = _activation_state(user, organization, workspace, can_write=False)

    daily_quality = payload["daily_quality"]
    assert daily_quality["mode"] == "permission_limited"
    assert daily_quality["primary_action"]["id"] == "request_workspace_access"
    assert payload["recommended_action"]["kind"] == "request_access"
    assert payload["email_eligibility"]["suppression_reason"] == "permission_limited"
