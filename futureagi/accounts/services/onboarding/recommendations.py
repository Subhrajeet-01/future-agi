WRITE_STAGES = {
    "choose_goal",
    "connect_observability",
    "waiting_for_first_trace",
    "waiting_for_first_trace_sample_available",
    "create_trace_evaluator",
}


def _route(routes, key):
    return routes.get(key, {"href": "", "is_available": False, "reason": "missing_id"})


def _action(
    *,
    action_id,
    kind,
    title,
    description,
    route_key,
    routes,
    cta_label,
    priority,
    fallback_href,
    estimated_minutes=None,
    requires_permission=None,
    completion_event=None,
    is_sample=False,
    target_path=None,
    source="home",
    blocked_reason=None,
):
    route = _route(routes, route_key)
    route_available = bool(route["is_available"])
    blocked = bool(blocked_reason) or not route_available
    reason = blocked_reason or route.get("reason")
    href = route["href"] if route_available else None
    return {
        "id": action_id,
        "kind": kind,
        "title": title,
        "description": description,
        "href": href,
        "cta_label": cta_label,
        "estimated_minutes": estimated_minutes,
        "priority": priority,
        "blocked": blocked,
        "blocked_reason": reason if blocked else None,
        "requires_permission": requires_permission,
        "completion_event": completion_event,
        "is_sample": is_sample,
        "route_available": route_available,
        "fallback_href": fallback_href,
        "analytics": {
            "event_name": "onboarding_recommended_action_clicked",
            "source": source,
            "target_path": target_path,
        },
    }


def get_started_action(routes):
    href = _route(routes, "get_started")["href"]
    return _action(
        action_id="open_get_started",
        kind="fallback",
        title="Open Get Started",
        description="Use the existing setup checklist.",
        route_key="get_started",
        routes=routes,
        cta_label="Open Get Started",
        priority=10,
        fallback_href=href,
        source="fallback",
    )


def sample_action(routes):
    fallback_href = _route(routes, "get_started")["href"]
    return _action(
        action_id="open_sample_trace",
        kind="sample_project",
        title="Open sample trace",
        description="Review a sample trace while real data is pending.",
        route_key="sample_trace",
        routes=routes,
        cta_label="Open sample trace",
        priority=30,
        fallback_href=fallback_href,
        completion_event="sample_signal_viewed",
        is_sample=True,
        target_path="sample",
    )


def request_access_action(routes):
    fallback_href = _route(routes, "get_started")["href"]
    return _action(
        action_id="request_workspace_access",
        kind="request_access",
        title="Request workspace access",
        description="Ask an admin for access before making onboarding changes.",
        route_key="workspace_list",
        routes=routes,
        cta_label="Request access",
        priority=90,
        fallback_href=fallback_href,
        source="permission_limited",
    )


def _fallback_for_stage(stage, flags, routes):
    if stage in {
        "connect_observability",
        "waiting_for_first_trace",
        "waiting_for_first_trace_sample_available",
    } and flags.get("onboarding_sample_project"):
        return sample_action(routes)
    if stage in {"daily_review", "activated"}:
        return _action(
            action_id="open_observe_dashboard_fallback",
            kind="review",
            title="Open observe dashboard",
            description="Review current observability signals.",
            route_key="observe_dashboard",
            routes=routes,
            cta_label="Open observe",
            priority=20,
            fallback_href=_route(routes, "get_started")["href"],
            target_path="observe",
        )
    return get_started_action(routes)


def resolve_recommended_action(*, context, flags, signals, stage, routes):
    fallback = _fallback_for_stage(stage, flags, routes)

    if stage == "feature_disabled":
        action = get_started_action(routes)
        return action, action
    if stage == "workspace_missing":
        return (
            _action(
                action_id="open_workspace_list",
                kind="fallback",
                title="Choose a workspace",
                description="Open workspace settings to choose or create a workspace.",
                route_key="workspace_list",
                routes=routes,
                cta_label="Open workspaces",
                priority=100,
                fallback_href=_route(routes, "get_started")["href"],
                source="workspace_missing",
            ),
            get_started_action(routes),
        )
    if stage == "permission_limited":
        return request_access_action(routes), fallback
    if stage == "choose_goal":
        return (
            _action(
                action_id="choose_onboarding_goal",
                kind="choose_goal",
                title="Choose your first goal",
                description="Pick the job you want FutureAGI to help with first.",
                route_key="choose_goal",
                routes=routes,
                cta_label="Choose goal",
                priority=100,
                fallback_href=fallback["fallback_href"],
                target_path=context.primary_path,
            ),
            fallback,
        )
    if stage == "connect_observability":
        return (
            _action(
                action_id="create_observe_project",
                kind="setup",
                title="Connect observability",
                description="Create an observability project and send one request.",
                route_key="observe_setup",
                routes=routes,
                cta_label="Connect observability",
                priority=100,
                fallback_href=fallback["fallback_href"],
                estimated_minutes=5,
                requires_permission="observe:write",
                completion_event="observe_project_created",
                target_path="observe",
            ),
            fallback,
        )
    if stage in {"waiting_for_first_trace", "waiting_for_first_trace_sample_available"}:
        return (
            _action(
                action_id="send_first_trace",
                kind="send_signal",
                title="Send your first trace",
                description="Send one production or test trace to unlock review.",
                route_key="observe_project",
                routes=routes,
                cta_label="Send trace",
                priority=100,
                fallback_href=fallback["fallback_href"],
                estimated_minutes=5,
                requires_permission="observe:write",
                completion_event="trace_ingested",
                target_path="observe",
            ),
            fallback,
        )
    if stage == "review_first_trace":
        return (
            _action(
                action_id="review_first_trace",
                kind="review",
                title="Review the first trace",
                description="Inspect latency, cost, and quality signal context.",
                route_key="observe_trace_detail",
                routes=routes,
                cta_label="Review trace",
                priority=100,
                fallback_href=fallback["fallback_href"],
                completion_event="trace_reviewed",
                target_path="observe",
            ),
            fallback,
        )
    if stage == "create_trace_evaluator":
        return (
            _action(
                action_id="create_trace_evaluator",
                kind="improve",
                title="Create an evaluator",
                description="Turn the reviewed trace into a repeatable quality check.",
                route_key="observe_project",
                routes=routes,
                cta_label="Create evaluator",
                priority=100,
                fallback_href=fallback["fallback_href"],
                estimated_minutes=5,
                requires_permission="observe:write",
                completion_event="first_quality_loop_completed",
                target_path="observe",
            ),
            fallback,
        )
    if stage == "daily_review":
        return (
            _action(
                action_id="review_daily_quality",
                kind="daily_quality",
                title="Review today’s quality signal",
                description="Open the daily quality view and resolve the top item.",
                route_key="daily_quality_home",
                routes=routes,
                cta_label="Review signal",
                priority=100,
                fallback_href=fallback["fallback_href"],
                completion_event="daily_quality_item_reviewed",
                target_path="observe",
            ),
            fallback,
        )
    if stage == "activated":
        return (
            _action(
                action_id="open_observe_dashboard",
                kind="review",
                title="Open observe dashboard",
                description="Review the current quality loop.",
                route_key="observe_dashboard",
                routes=routes,
                cta_label="Open observe",
                priority=80,
                fallback_href=_route(routes, "get_started")["href"],
                target_path="observe",
            ),
            fallback,
        )
    return (
        _action(
            action_id="choose_available_path",
            kind="fallback",
            title="Choose an available path",
            description="Start with the observe path while this path is unavailable.",
            route_key="observe_setup",
            routes=routes,
            cta_label="Start with observe",
            priority=80,
            fallback_href=fallback["fallback_href"],
            target_path="observe",
        ),
        fallback,
    )
