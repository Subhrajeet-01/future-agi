import pytest
from django.test import override_settings
from rest_framework import status


@pytest.mark.django_db
def test_activation_state_requires_auth(api_client):
    response = api_client.get("/accounts/activation-state/")

    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }


@pytest.mark.django_db
@override_settings(ONBOARDING_FEATURE_FLAGS={})
def test_activation_state_flag_off_returns_renderable_payload(auth_client):
    response = auth_client.get("/accounts/activation-state/")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()["result"]
    assert payload["stage"] == "feature_disabled"
    assert payload["recommended_action"]["id"] == "open_get_started"


@pytest.mark.django_db
@override_settings(
    ONBOARDING_FEATURE_FLAGS={
        "onboarding_activation_state_api": True,
        "onboarding_goal_picker": True,
        "onboarding_path_cards": True,
    }
)
def test_activation_state_flag_on_returns_full_shape(auth_client, user):
    user.goals = ["monitor_production_ai_app"]
    user.role = "developer"
    user.save(update_fields=["goals", "role"])

    response = auth_client.get("/accounts/activation-state/")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()["result"]
    assert payload["stage"] == "connect_observability"
    for key in [
        "schema_version",
        "workspace_id",
        "organization_id",
        "recommended_action",
        "fallback_action",
        "progress",
        "signals",
        "available_paths",
        "sample_project",
        "email_eligibility",
        "permissions",
        "feature_flags",
        "route_availability",
        "warnings",
    ]:
        assert key in payload


@pytest.mark.django_db
@override_settings(ONBOARDING_FEATURE_FLAGS={"onboarding_activation_state_api": True})
def test_activation_state_unknown_query_param_does_not_crash(auth_client, user):
    user.goals = ["monitor_production_ai_app"]
    user.save(update_fields=["goals"])

    response = auth_client.get("/accounts/activation-state/?unexpected=value")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"]["stage"] == "connect_observability"


@pytest.mark.django_db
@override_settings(ONBOARDING_FEATURE_FLAGS={"onboarding_activation_state_api": True})
def test_activation_state_stale_email_query_reflects_current_state(auth_client, user):
    user.goals = ["monitor_production_ai_app"]
    user.save(update_fields=["goals"])

    response = auth_client.get(
        "/accounts/activation-state/?target_stage=activated&target_event=first_quality_loop_completed"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"]["stage"] == "connect_observability"
