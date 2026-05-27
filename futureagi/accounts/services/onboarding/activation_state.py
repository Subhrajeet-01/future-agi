import uuid

from django.utils import timezone

from accounts.serializers.onboarding import ActivationStateResponseSerializer
from accounts.services.onboarding.constants import ACTIVATION_SCHEMA_VERSION
from accounts.services.onboarding.context import resolve_onboarding_context
from accounts.services.onboarding.feature_flags import get_onboarding_flags
from accounts.services.onboarding.flow_config import (
    configured_goal_options,
    configured_path,
    configured_stage_copy,
    configured_stage_home_mode,
    configured_stage_progress,
    resolve_stage_from_config,
)
from accounts.services.onboarding.recommendations import (
    WRITE_STAGES,
    resolve_recommended_action,
)
from accounts.services.onboarding.route_availability import resolve_route_availability
from accounts.services.onboarding.signal_resolver import (
    OnboardingSignals,
    collect_onboarding_signals,
)


def _empty_signals():
    return OnboardingSignals(first_checks={})


def _base_stage(context, flags, signals):
    return resolve_stage_from_config(context=context, flags=flags, signals=signals)


def _stage_for_context(context, flags, signals):
    stage = _base_stage(context, flags, signals)
    if context.permissions["permission_limited"] and stage in WRITE_STAGES:
        return "permission_limited"
    return stage


def _available_paths(context, flags, routes):
    selected_path = context.primary_path
    path_ids = ["observe", "sample"]
    if selected_path and selected_path not in path_ids:
        path_ids.insert(0, selected_path)

    paths = []
    for path_id in path_ids:
        path_config = configured_path(path_id)
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
                "label": path_config["label"],
                "description": path_config["description"],
                "status": status,
                "href": route.get("href") or f"/dashboard/home?path={path_id}",
                "is_available": is_available,
                "blocked_reason": None if is_available else route.get("reason"),
                "requires_permission": path_config["requires_permission"],
                "first_action_id": path_config["first_action_id"],
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
        "stage_copy": configured_stage_copy(stage),
        "home_mode": configured_stage_home_mode(stage),
        "is_activated": is_activated,
        "activated_at": (
            signals.last_meaningful_event.occurred_at
            if is_activated and signals.last_meaningful_event
            else None
        ),
        "recommended_action": recommended_action,
        "fallback_action": fallback_action,
        "progress": configured_stage_progress(stage),
        "signals": signals.to_payload(),
        "available_goals": configured_goal_options(),
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
