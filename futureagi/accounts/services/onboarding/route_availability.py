from accounts.services.onboarding.constants import PRODUCT_PATHS


def route_entry(href, is_available=True, reason=None):
    return {
        "href": href,
        "is_available": is_available,
        "reason": None if is_available else reason,
    }


def _available_if(flag, href, reason="feature_disabled"):
    return route_entry(href, is_available=bool(flag), reason=reason)


def _sample_route(flags, sample_project):
    if not flags.get("onboarding_sample_project"):
        return _available_if(False, "/dashboard/home?sample=true")
    if not sample_project:
        return route_entry("/dashboard/home?sample=true")
    if sample_project.get("is_hidden"):
        return route_entry(
            sample_project.get("href") or "/dashboard/home?sample=true",
            is_available=False,
            reason=sample_project.get("blocked_reason") or "sample_hidden",
        )
    if not sample_project.get("available"):
        return route_entry(
            sample_project.get("href") or "/dashboard/home?sample=true",
            is_available=False,
            reason=sample_project.get("blocked_reason") or "sample_artifact_missing",
        )
    return route_entry(
        sample_project.get("entry_route")
        or sample_project.get("href")
        or "/dashboard/home?sample=true"
    )


def resolve_route_availability(*, context, flags, signals, sample_project=None):
    can_write = context.permissions["can_write"]
    first_observe_id = signals.first_observe_id
    first_trace_id = signals.first_trace_id
    prompt_id = signals.latest_prompt_id or signals.first_prompt_id
    prompt_route_modes_enabled = bool(flags.get("onboarding_prompt_route_modes"))
    prompt_path_enabled = bool(flags.get("onboarding_prompt_path"))

    prompt_workbench_href = "/dashboard/workbench/all?source=onboarding"
    prompt_create_href = (
        f"{prompt_workbench_href}&action=create-prompt"
        if prompt_route_modes_enabled
        else "/dashboard/workbench/all"
    )
    prompt_editor_href = (
        f"/dashboard/workbench/create/{prompt_id}"
        if prompt_id
        else "/dashboard/workbench/all"
    )

    def prompt_route(mode, fallback_reason="missing_id", requires_write=True):
        if not prompt_path_enabled:
            return route_entry(
                prompt_editor_href,
                is_available=False,
                reason="feature_disabled",
            )
        if requires_write and not can_write:
            return route_entry(
                prompt_editor_href,
                is_available=False,
                reason="missing_permission",
            )
        if not prompt_id:
            return route_entry(
                prompt_workbench_href,
                is_available=False,
                reason=fallback_reason,
            )
        suffix = (
            f"?source=onboarding&onboarding={mode}"
            if prompt_route_modes_enabled
            else ""
        )
        return route_entry(f"{prompt_editor_href}{suffix}", is_available=True)

    routes = {
        "home": route_entry("/dashboard/home"),
        "get_started": route_entry("/dashboard/get-started"),
        "workspace_list": route_entry("/dashboard/settings/user-management"),
        "choose_goal": _available_if(
            flags.get("onboarding_goal_picker"),
            "/dashboard/home?mode=choose-goal",
        ),
        "observe_setup": route_entry(
            "/dashboard/observe?setup=true&source=onboarding",
            is_available=can_write,
            reason="missing_permission",
        ),
        "observe_project": route_entry(
            f"/dashboard/observe/{first_observe_id}"
            if first_observe_id
            else "/dashboard/observe",
            is_available=bool(first_observe_id),
            reason="missing_id",
        ),
        "observe_trace_detail": route_entry(
            (
                f"/dashboard/observe/{first_observe_id}/trace/{first_trace_id}"
                if first_observe_id and first_trace_id
                else "/dashboard/observe"
            ),
            is_available=bool(first_observe_id and first_trace_id),
            reason="missing_id",
        ),
        "observe_dashboard": route_entry(
            f"/dashboard/observe/{first_observe_id}"
            if first_observe_id
            else "/dashboard/observe",
            is_available=True,
        ),
        "sample_trace": _sample_route(flags, sample_project),
        "support": route_entry("/dashboard/get-started?support=true"),
        "daily_quality_home": _available_if(
            flags.get("onboarding_daily_quality_home"),
            "/dashboard/home?mode=daily-quality",
        ),
        "prompt_workbench": _available_if(
            prompt_path_enabled,
            prompt_workbench_href,
        ),
        "prompt_create": route_entry(
            prompt_create_href,
            is_available=prompt_path_enabled and can_write,
            reason="missing_permission" if prompt_path_enabled else "feature_disabled",
        ),
        "prompt_run_test": prompt_route("run-test"),
        "prompt_save_version": prompt_route("save-version"),
        "prompt_compare_versions": prompt_route("compare"),
        "prompt_add_failure": prompt_route("add-failure"),
        "prompt_metrics": prompt_route("metrics", requires_write=False),
    }

    for path in PRODUCT_PATHS:
        sample_hidden = (
            path == "sample" and sample_project and sample_project["is_hidden"]
        )
        routes[f"path_{path}"] = route_entry(
            f"/dashboard/home?path={path}",
            is_available=(
                path in {"observe", "sample"}
                or (path == "prompt" and prompt_path_enabled)
            )
            and not sample_hidden,
            reason=(
                sample_project.get("blocked_reason") or "sample_hidden"
                if sample_hidden
                else "route_not_implemented"
            ),
        )
    return routes
