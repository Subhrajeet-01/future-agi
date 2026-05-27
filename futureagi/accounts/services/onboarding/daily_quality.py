from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import Q

from accounts.services.onboarding.activation_events import latest_event
from accounts.services.onboarding.route_availability import route_entry

REVIEW_EVENTS = (
    "daily_quality_item_reviewed",
    "daily_quality_top_change_reviewed",
    "daily_quality_action_completed",
)


@dataclass(frozen=True)
class DailyQualityResult:
    state: dict
    recommended_action: dict | None
    route_availability: dict = field(default_factory=dict)


def _internal_route(href):
    return isinstance(href, str) and href.startswith("/") and not href.startswith("//")


def _route(routes, key, fallback="/dashboard/get-started"):
    return routes.get(key) or route_entry(
        fallback, is_available=False, reason="missing_id"
    )


def _last_reviewed_at(context):
    if not context.organization or not context.workspace:
        return None
    event = latest_event(
        organization=context.organization,
        workspace=context.workspace,
        event_names=REVIEW_EVENTS,
        product_path="observe",
        is_sample=False,
    )
    return event.occurred_at if event else None


def _first_quality_loop_at(context):
    if not context.organization or not context.workspace:
        return None
    event = latest_event(
        organization=context.organization,
        workspace=context.workspace,
        event_names=["first_quality_loop_completed"],
        product_path="observe",
        is_sample=False,
    )
    return event.occurred_at if event else None


def _window(context, signals, now):
    last_reviewed_at = _last_reviewed_at(context)
    activated_at = _first_quality_loop_at(context)
    if not activated_at and signals.last_meaningful_event:
        activated_at = signals.last_meaningful_event.occurred_at
    earliest = now - timedelta(days=7)
    starts = [value for value in (last_reviewed_at, activated_at, earliest) if value]
    return {
        "last_reviewed_at": last_reviewed_at,
        "start_at": max(starts) if starts else earliest,
        "end_at": now,
    }


def _trace_queryset(context):
    from tracer.models.trace import Trace

    return (
        Trace.no_workspace_objects.filter(
            project__organization=context.organization,
            project__workspace=context.workspace,
            project__trace_type="observe",
        )
        .exclude(project__source="sample")
        .filter(
            Q(project__metadata__is_sample__isnull=True)
            | Q(project__metadata__is_sample=False)
        )
        .filter(Q(metadata__is_sample__isnull=True) | Q(metadata__is_sample=False))
    )


def _trace_failure_signal(context, review_window):
    trace = (
        _trace_queryset(context)
        .filter(
            created_at__gt=review_window["start_at"],
            created_at__lte=review_window["end_at"],
            error__isnull=False,
        )
        .select_related("project")
        .order_by("-created_at", "id")
        .first()
    )
    if not trace or trace.error in ({}, [], ""):
        return None, {}

    route = f"/dashboard/observe/{trace.project_id}/trace/{trace.id}"
    return (
        {
            "id": f"trace_failure:{trace.id}",
            "type": "trace_failure",
            "severity": "critical",
            "title": "Review the latest failed trace",
            "body": "A real observe trace failed since the last quality review.",
            "source_type": "trace",
            "source_id": str(trace.id),
            "project_id": str(trace.project_id),
            "route": route,
            "is_sample": False,
            "created_at": trace.created_at,
        },
        {
            "daily_quality_signal": route_entry(route),
        },
    )


def _observe_route(routes):
    for key in ("observe_project", "observe_dashboard", "get_started"):
        route = _route(routes, key)
        if route.get("is_available") and _internal_route(route.get("href")):
            return route["href"], []
    return "/dashboard/get-started", ["route_fallback_used"]


def _request_access_action(context):
    route = (
        context.permissions.get("request_access_href")
        or "/dashboard/settings/user-management"
    )
    if not _internal_route(route):
        route = "/dashboard/settings/user-management"
    return {
        "id": "request_workspace_access",
        "label": "Request access",
        "body": "Ask an admin for workspace access before changing the quality setup.",
        "route": route,
        "fallback_route": "/dashboard/get-started",
        "route_available": True,
        "source_type": "workspace",
        "source_id": str(context.workspace.id) if context.workspace else None,
        "success_event": None,
        "is_primary": True,
        "is_sample": False,
        "requires_permission": None,
        "activation_kind": "request_access",
    }


def _next_action(context, signals, routes):
    route, diagnostics = _observe_route(routes)
    source_id = signals.first_observe_id or (
        str(context.workspace.id) if context.workspace else None
    )
    write_action = None
    if not signals.evaluator_exists:
        write_action = {
            "id": "create_trace_evaluator",
            "label": "Create evaluator",
            "body": "Turn reviewed traces into repeatable quality coverage.",
            "success_event": "first_quality_loop_completed",
        }
    elif not signals.alert_exists:
        write_action = {
            "id": "create_trace_alert",
            "label": "Create alert",
            "body": "Get notified when a future trace needs attention.",
            "success_event": "first_quality_loop_completed",
        }
    elif not signals.dashboard_exists:
        write_action = {
            "id": "create_trace_dashboard",
            "label": "Create dashboard",
            "body": "Give the team one place to review trace health.",
            "success_event": "first_quality_loop_completed",
        }
    elif not signals.saved_view_exists:
        write_action = {
            "id": "save_trace_view",
            "label": "Save trace view",
            "body": "Keep the recurring trace review filter one click away.",
            "success_event": "first_quality_loop_completed",
        }

    if write_action and not context.permissions["can_write"]:
        return _request_access_action(context), ["permission_limited"]

    if not write_action:
        return (
            {
                "id": "open_observe_project",
                "label": "Open observe",
                "body": "Review the current observe project and recent traces.",
                "route": route,
                "fallback_route": "/dashboard/get-started",
                "route_available": True,
                "source_type": "project" if signals.first_observe_id else "workspace",
                "source_id": source_id,
                "success_event": None,
                "is_primary": True,
                "is_sample": False,
                "requires_permission": None,
                "activation_kind": "daily_quality",
            },
            diagnostics,
        )

    return (
        {
            **write_action,
            "route": route,
            "fallback_route": "/dashboard/get-started",
            "route_available": True,
            "source_type": "project" if signals.first_observe_id else "workspace",
            "source_id": source_id,
            "is_primary": True,
            "is_sample": False,
            "requires_permission": "observe:write",
            "activation_kind": "daily_quality",
        },
        [*diagnostics, "route_fallback_used"],
    )


def _signal_action(top_signal):
    return {
        "id": "review_failed_trace",
        "label": "Review trace",
        "body": "Open the failed trace and inspect the failure context.",
        "route": top_signal["route"],
        "fallback_route": "/dashboard/get-started",
        "route_available": True,
        "source_type": top_signal["source_type"],
        "source_id": top_signal["source_id"],
        "success_event": "daily_quality_item_reviewed",
        "is_primary": True,
        "is_sample": False,
        "requires_permission": None,
        "activation_kind": "daily_quality",
    }


def _product_card(*, mode, top_signal, action, routes):
    route = _route(routes, "observe_project").get("href") or _route(
        routes, "observe_dashboard"
    ).get("href")
    if not _internal_route(route):
        route = "/dashboard/observe"
    if top_signal:
        return {
            "path": "observe",
            "status": "needs_review",
            "label": "Observe",
            "summary": "1 trace failure needs review",
            "metric": "1",
            "change": "New since last review",
            "route": route,
        }
    if mode == "permission_limited":
        return {
            "path": "observe",
            "status": "permission_limited",
            "label": "Observe",
            "summary": "Access needed for the next setup action",
            "metric": "View",
            "change": "No new signal",
            "route": route,
        }
    return {
        "path": "observe",
        "status": "healthy",
        "label": "Observe",
        "summary": action["label"],
        "metric": "0",
        "change": "No new signal",
        "route": route,
    }


def _activation_action(action, fallback_href="/dashboard/get-started"):
    route_available = bool(action.get("route_available", True))
    return {
        "id": action["id"],
        "kind": action.get("activation_kind") or "daily_quality",
        "title": action["label"],
        "description": action["body"],
        "href": action.get("route") if route_available else None,
        "cta_label": action["label"],
        "estimated_minutes": 4,
        "priority": 100,
        "blocked": not route_available,
        "blocked_reason": None if route_available else "route_unavailable",
        "requires_permission": action.get("requires_permission"),
        "completion_event": action.get("success_event"),
        "is_sample": bool(action.get("is_sample")),
        "route_available": route_available,
        "fallback_href": action.get("fallback_route") or fallback_href,
        "analytics": {
            "event_name": "daily_quality_action_opened",
            "source": "daily_quality_home",
            "target_path": "observe",
        },
    }


def _unavailable(reason, now):
    return {
        "mode": "unavailable",
        "last_reviewed_at": None,
        "window": {
            "start_at": now,
            "end_at": now,
        },
        "top_signal": None,
        "primary_action": None,
        "action_cards": [],
        "product_cards": [],
        "digest_eligible": False,
        "digest_suppression_reason": reason,
        "diagnostics": [reason],
    }


def resolve_daily_quality_state(*, context, flags, signals, routes, stage, now):
    if not flags.get("onboarding_daily_quality_home"):
        return DailyQualityResult(_unavailable("flag_disabled", now), None)
    if stage not in {"activated", "daily_review"} or not signals.first_loop_completed:
        return DailyQualityResult(_unavailable("not_activated", now), None)
    if context.primary_path != "observe":
        return DailyQualityResult(_unavailable("path_changed", now), None)
    if signals.last_meaningful_event and signals.last_meaningful_event.is_sample:
        return DailyQualityResult(_unavailable("sample_only", now), None)

    review_window = _window(context, signals, now)
    top_signal, route_availability = _trace_failure_signal(context, review_window)
    diagnostics = []

    if top_signal:
        mode = "new_signal"
        primary_action = _signal_action(top_signal)
        digest_eligible = bool(flags.get("onboarding_email_daily_digest_enabled"))
        digest_suppression_reason = None if digest_eligible else "flag_disabled"
    else:
        primary_action, diagnostics = _next_action(context, signals, routes)
        mode = (
            "permission_limited"
            if "permission_limited" in diagnostics
            else "no_new_signal"
        )
        digest_eligible = False
        digest_suppression_reason = (
            "permission_limited" if mode == "permission_limited" else "no_useful_signal"
        )
        diagnostics = diagnostics or ["no_new_signal"]

    state = {
        "mode": mode,
        "last_reviewed_at": review_window["last_reviewed_at"],
        "window": {
            "start_at": review_window["start_at"],
            "end_at": review_window["end_at"],
        },
        "top_signal": top_signal,
        "primary_action": primary_action,
        "action_cards": [],
        "product_cards": [
            _product_card(
                mode=mode,
                top_signal=top_signal,
                action=primary_action,
                routes=routes,
            )
        ],
        "digest_eligible": digest_eligible,
        "digest_suppression_reason": digest_suppression_reason,
        "diagnostics": diagnostics,
    }
    return DailyQualityResult(
        state=state,
        recommended_action=_activation_action(primary_action),
        route_availability=route_availability,
    )
