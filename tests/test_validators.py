from custom_components.ha_llm_automation_builder.validators import dry_run_automation_yaml, validate_automation_yaml


def test_validate_ok_yaml():
    yaml_text = """
alias: Test
trigger: []
action: []
"""
    result = validate_automation_yaml(yaml_text)
    assert result.valid


def test_validate_missing_trigger():
    yaml_text = "action: []"
    result = validate_automation_yaml(yaml_text)
    assert not result.valid
    assert "Missing required key: trigger" in result.errors


def test_validate_semantic_missing_platform_trigger():
    yaml_text = '{"alias":"Test","trigger":{"entity_id":"light.kitchen"},"action":[]}'
    result = validate_automation_yaml(yaml_text)
    assert not result.valid
    assert "missing required field: platform" in result.errors[0].lower()


def test_validate_nonexistent_entity_with_known_registry():
    yaml_text = '{"alias":"Test","trigger":{"platform":"state","entity_id":"light.unknown"},"action":[]}'
    result = validate_automation_yaml(yaml_text, known_entities={"light.kitchen"})
    assert not result.valid
    assert any("does not exist" in err for err in result.errors)


def test_dry_run_state_trigger_and_condition():
    yaml_text = (
        '{"alias":"Test","trigger":{"platform":"state","entity_id":"binary_sensor.motion","to":"on"},'
        '"condition":{"condition":"state","entity_id":"light.kitchen","state":"off"},'
        '"action":[{"service":"light.turn_on","target":{"entity_id":"light.kitchen"}}]}'
    )
    result = dry_run_automation_yaml(
        yaml_text,
        entity_states={"binary_sensor.motion": "on", "light.kitchen": "off"},
        known_entities={"binary_sensor.motion", "light.kitchen"},
    )
    assert result.valid
    assert result.trigger_matches
    assert result.conditions_passed
    assert result.would_execute
