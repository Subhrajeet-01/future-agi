from copy import deepcopy

import pytest
from django.core.exceptions import ImproperlyConfigured

from accounts.services.onboarding.flow_config import (
    _validate_config,
    get_activation_flow_config,
)


def _valid_activation_flow_config():
    return deepcopy(get_activation_flow_config())


def test_activation_flow_rejects_duplicate_activation_event_names():
    config = _valid_activation_flow_config()
    event_name = config["activation_events"]["names"][0]
    config["activation_events"]["names"].append(event_name)

    with pytest.raises(ImproperlyConfigured):
        _validate_config(config)


@pytest.mark.parametrize("route_field", ("route_key", "fallback_route_key"))
def test_activation_flow_rejects_unknown_action_route_keys(route_field):
    config = _valid_activation_flow_config()
    config["actions"]["create_prompt"][route_field] = "missing_route"

    with pytest.raises(ImproperlyConfigured):
        _validate_config(config)


def test_activation_flow_rejects_unknown_stage_rule_feature_flags():
    config = _valid_activation_flow_config()
    config["stage_rules"][0]["when"] = {
        "flag_enabled": "onboarding_flag_that_does_not_exist",
    }

    with pytest.raises(ImproperlyConfigured):
        _validate_config(config)
