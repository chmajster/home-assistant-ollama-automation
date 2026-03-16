from custom_components.ha_llm_automation_builder.validators import validate_automation_yaml


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
