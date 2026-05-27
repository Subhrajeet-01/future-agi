import uuid

from django.utils import timezone

from accounts.serializers.onboarding import ActivationStateResponseSerializer
from accounts.services.onboarding.constants import ACTIVATION_SCHEMA_VERSION
from accounts.services.onboarding.context import resolve_onboarding_context
from accounts.services.onboarding.feature_flags import get_onboarding_flags
from accounts.services.onboarding.recommendations import (
    WRITE_STAGES,
    resolve_recommended_action,
)
from accounts.services.onboarding.route_availability import resolve_route_availability
from accounts.services.onboarding.signal_resolver import (
    OnboardingSignals,
    collect_onboarding_signals,
)

PATH_COPY = {
    "observe": {
        "label": "Monitor a production AI app",
        "description": "Connect traces and inspect quality signals.",
        "first_action_id": "create_observe_project",
        "requires_permission": "observe:write",
    },
    "sample": {
        "label": "Explore with sample data",
        "description": "Use a sample workspace while real data is pending.",
        "first_action_id": "open_sample_trace",
        "requires_permission": None,
    },
    "prompt": {
        "label": "Improve prompts",
        "description": "Test and compare prompt versions.",
        "first_action_id": None,
        "requires_permission": "prompt:write",
    },
    "agent": {
        "label": "Build an AI agent",
        "description": "Create an agent and review its first scenario.",
        "first_action_id": None,
        "requires_permission": "agent:write",
    },
    "gateway": {
        "label": "Control model traffic",
        "description": "Configure model routing and production policies.",
        "first_action_id": None,
        "requires_permission": "gateway:write",
    },
    "voice": {
        "label": "Connect a voice AI agent",
        "description": "Review calls and success criteria.",
        "first_action_id": None,
        "requires_permission": "voice:write",
    },
    "evals": {
        "label": "Evaluate quality",
        "description": "Create datasets, scorers, and failure review loops.",
        "first_action_id": None,
        "requires_permission": "evals:write",
    },
    "dashboards": {
        "label": "Build quality dashboards",
        "description": "Track quality, cost, latency, and failures.",
        "first_action_id": None,
        "requires_permission": "dashboards:write",
    },
}


def _empty_signals():
    return OnboardingSignals(first_checks={})


def _base_stage(context, flags, signals):
    if not flags.get("onboarding_activation_state_api"):
        return "feature_disabled"
    if not context.organization or not context.workspace:
        return "workspace_missing"
    if not context.selected_goal:
        return "choose_goal"
    if context.primary_path != "observe":
        return "selected_path_unavailable"
    if signals.first_loop_completed:
        if flags.get("onboarding_daily_quality_home") and signals.useful_daily_signal:
            return "daily_review"
        return "activated"
    if not signals.observe_project_exists:
        return "connect_observability"
    if signals.observe_project_exists and not signals.trace_exists:
        if flags.get("onboarding_sample_project"):
            return "waiting_for_first_trace_sample_available"
        return "waiting_for_first_trace"
    if signals.trace_exists and not signals.trace_reviewed:
        return "review_first_trace"
    if signals.trace_reviewed and not (
        signals.evaluator_exists
        or signals.dashboard_exists
        or signals.alert_exists
        or signals.saved_view_exists
    ):
        return "create_trace_evaluator"
    return "activated"


def _stage_for_context(context, flags, signals):
    stage = _base_stage(context, flags, signals)
    if context.permissions["permission_limited"] and stage in WRITE_STAGES:
        return "permission_limited"
    return stage


def _home_mode(stage):
    if stage == "daily_review":
        return "daily_quality"
    if stage in {
        "feature_disabled",
        "workspace_missing",
        "selected_path_unavailable",
        "permission_limited",
    }:
        return "fallback"
    return "first_run"


def _progress(stage):
    if stage in {"feature_disabled", "workspace_missing", "choose_goal"}:
        return {
            "build": "not_started",
            "test": "available",
            "observe": "not_started",
            "ship": "available",
            "improve": "available",
        }
    if stage in {"connect_observability", "permission_limited"}:
        return {
            "build": "selected",
            "test": "available",
            "observe": "not_started",
            "ship": "available",
            "improve": "available",
        }
    if stage in {"waiting_for_first_trace", "waiting_for_first_trace_sample_available"}:
        return {
            "build": "selected",
            "test": "available",
            "observe": "in_progress",
            "ship": "available",
            "improve": "available",
        }
    if stage == "review_first_trace":
        return {
            "build": "selected",
            "test": "available",
            "observe": "in_progress",
            "ship": "available",
            "improve": "available",
        }
    if stage == "create_trace_evaluator":
        return {
            "build": "selected",
            "test": "available",
            "observe": "complete",
            "ship": "available",
            "improve": "in_progress",
        }
    if stage in {"activated", "daily_review"}:
        return {
            "build": "complete",
            "test": "available",
            "observe": "complete",
            "ship": "available",
            "improve": "complete",
        }
    return {
        "build": "selected",
        "test": "available",
        "observe": "available",
        "ship": "available",
        "improve": "available",
    }


def _available_paths(context, flags, routes):
    selected_path = context.primary_path
    path_ids = ["observe", "sample"]
    if selected_path and selected_path not in path_ids:
        path_ids.insert(0, selected_path)

    paths = []
    for path_id in path_ids:
        copy = PATH_COPY[path_id]
        route = routes.get(f"path_{path_id}", {})
        is_available = bool(route.get("is_available"))
        status = "available" if is_available else "hidden"
        if path_id == selected_path and is_available:
            status = "selected"
        elif path_id == "sample" and not flags.get("onboarding_sample_project"):
            status = "hidden"
            is_available = False
        paths.append(
            {
                "id": path_id,
                "label": copy["label"],
                "description": copy["description"],
                "status": status,
                "href": route.get("href") or f"/dashboard/home?path={path_id}",
                "is_available": is_available,
                "blocked_reason": None if is_available else route.get("reason"),
                "requires_permission": copy["requires_permission"],
                "first_action_id": copy["first_action_id"],
            }
        )
    return paths


def _sample_project(flags):
    enabled = bool(flags.get("onboarding_sample_project"))
    return {
        "available": enabled,
        "created": False,
        "status": "available" if enabled else "unavailable",
        "href": "/dashboard/home?sample=true" if enabled else None,
        "version": "sample-observe-v1" if enabled else None,
        "is_hidden": not enabled,
        "hidden_reason": None if enabled else "feature_disabled",
        "entry_routes": [],
        "missing_artifacts": [],
        "last_opened_at": None,
    }


def _email_eligibility(stage, flags, now):
    suppressed = stage in {"feature_disabled", "workspace_missing", "activated"}
    reason = None
    if stage == "feature_disabled":
        reason = "feature_disabled"
    elif stage == "workspace_missing":
        reason = "workspace_suppressed"
    elif stage == "activated":
        reason = "activated"
    return {
        "eligible": not suppressed,
        "suppressed": suppressed,
        "suppression_reason": reason,
        "next_email_key": None if suppressed else f"{stage}_next",
        "next_email_after": None if suppressed else now,
        "digest_eligible": stage in {"activated", "daily_review"},
        "last_email_sent_at": None,
        "frequency_cap_remaining": 2,
        "dry_run_only": not bool(flags.get("onboarding_lifecycle_send_enabled")),
    }


def _last_event_payload(event):
    if not event:
        return None
    return {
        "name": event.event_name,
        "occurred_at": event.occurred_at,
        "is_sample": event.is_sample,
        "path": event.product_path or None,
        "metadata": event.metadata or {},
    }


def _validate_payload(payload):
    serializer = ActivationStateResponseSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def resolve_activation_state(*, context, flags, signals):
    stage = _stage_for_context(context, flags, signals)
    routes = resolve_route_availability(context=context, flags=flags, signals=signals)
    recommended_action, fallback_action = resolve_recommended_action(
        context=context,
        flags=flags,
        signals=signals,
        stage=stage,
        routes=routes,
    )
    now = timezone.now()
    is_activated = stage in {"activated", "daily_review"}
    payload = {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "request_id": f"req_{uuid.uuid4().hex}",
        "server_time": now,
        "workspace_id": str(context.workspace.id) if context.workspace else None,
        "organization_id": (
            str(context.organization.id) if context.organization else None
        ),
        "user_id": str(context.user.id),
        "goal": context.selected_goal,
        "persona": context.persona,
        "primary_path": context.primary_path,
        "stage": stage,
        "home_mode": _home_mode(stage),
        "is_activated": is_activated,
        "activated_at": (
            signals.last_meaningful_event.occurred_at
            if is_activated and signals.last_meaningful_event
            else None
        ),
        "recommended_action": recommended_action,
        "fallback_action": fallback_action,
        "progress": _progress(stage),
        "signals": signals.to_payload(),
        "available_paths": _available_paths(context, flags, routes),
        "sample_project": _sample_project(flags),
        "email_eligibility": _email_eligibility(stage, flags, now),
        "permissions": context.permissions,
        "feature_flags": flags,
        "route_availability": routes,
        "email_context": None,
        "last_meaningful_event": _last_event_payload(signals.last_meaningful_event),
        "diagnostics": None,
        "warnings": context.warnings,
    }
    return _validate_payload(payload)


def resolve_activation_state_for_request(request):
    context = resolve_onboarding_context(request)
    flags = get_onboarding_flags(
        user=context.user,
        organization=context.organization,
        workspace=context.workspace,
    )
    if not flags.get("onboarding_activation_state_api"):
        signals = _empty_signals()
    elif not context.organization or not context.workspace:
        signals = _empty_signals()
    else:
        signals = collect_onboarding_signals(
            user=context.user,
            organization=context.organization,
            workspace=context.workspace,
        )
    return resolve_activation_state(context=context, flags=flags, signals=signals)
