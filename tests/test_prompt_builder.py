from custom_components.ha_llm_automation_builder.helpers.prompt_builder import build_prompt


def test_prompt_contains_safe_rule():
    prompt = build_prompt("test", "pl", True, template="swiatla", entity_hints=["light.test"])
    assert "Return Home Assistant automation YAML only" in prompt
    assert "light.test" in prompt
