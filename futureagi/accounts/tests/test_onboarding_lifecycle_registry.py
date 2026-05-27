from accounts.services.onboarding.constants import ONBOARDING_ACTIVATION_EVENTS
from accounts.services.onboarding.lifecycle_registry import lifecycle_campaigns


def test_lifecycle_campaign_registry_is_editable_and_valid():
    campaigns = lifecycle_campaigns()
    keys = [campaign["campaign_key"] for campaign in campaigns]

    assert len(campaigns) == 13
    assert len(keys) == len(set(keys))
    assert "welcome_choose_goal" in keys
    assert "observe_sample_bridge" in keys
    assert "prompt_create_first" in keys
    assert "prompt_add_failure_example" in keys
    for campaign in campaigns:
        assert campaign["template_key"].endswith("_v1")
        assert campaign["send_flag"] == "onboarding_lifecycle_send_enabled"
        assert campaign["target_success_event"] in ONBOARDING_ACTIVATION_EVENTS


def test_sample_bridge_campaign_is_configured_as_sample_only():
    campaign = next(
        campaign
        for campaign in lifecycle_campaigns()
        if campaign["campaign_key"] == "observe_sample_bridge"
    )

    assert campaign["sample_policy"] == "sample_only"
    assert campaign["route_strategy"] == "sample_project"
    assert campaign["dry_run_flag"] == "onboarding_email_sample_bridge_enabled"


def test_prompt_campaigns_are_configured_as_real_only():
    campaigns = [
        campaign
        for campaign in lifecycle_campaigns()
        if campaign["campaign_group"] == "prompt"
    ]

    assert len(campaigns) == 5
    for campaign in campaigns:
        assert campaign["primary_path"] == "prompt"
        assert campaign["sample_policy"] == "real_only"
        assert campaign["route_strategy"] == "activation_recommendation"
        assert campaign["dry_run_flag"] == "onboarding_email_prompt_enabled"
