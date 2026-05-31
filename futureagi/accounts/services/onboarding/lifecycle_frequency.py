from datetime import timedelta

from accounts.models import OnboardingLifecycleEvaluationLog
from accounts.services.onboarding.lifecycle_send_policy import (
    eligibility_frequency_caps,
)


def _eligible_logs_for_cap(*, user, workspace, campaign, now, cap):
    queryset = OnboardingLifecycleEvaluationLog.no_workspace_objects.filter(
        status=OnboardingLifecycleEvaluationLog.STATUS_ELIGIBLE,
    )
    window_hours = cap.get("window_hours")
    if window_hours is not None:
        queryset = queryset.filter(
            evaluated_at__gte=now - timedelta(hours=window_hours)
        )

    scope = cap["scope"]
    if scope == "user":
        return queryset.filter(user=user)
    if scope == "workspace":
        return queryset.filter(workspace=workspace)
    if scope == "campaign_user":
        return queryset.filter(user=user, campaign_key=campaign["campaign_key"])
    return queryset.none()


def frequency_cap_suppression(*, user, workspace, campaign, now):
    if not user or not workspace or not campaign:
        return None

    for cap in eligibility_frequency_caps():
        eligible_logs = _eligible_logs_for_cap(
            user=user,
            workspace=workspace,
            campaign=campaign,
            now=now,
            cap=cap,
        )
        if eligible_logs.count() >= cap["limit"]:
            return cap["reason"]

    return None
