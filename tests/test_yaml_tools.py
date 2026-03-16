from custom_components.ha_llm_automation_builder.helpers.yaml_tools import extract_llm_payload_text, parse_yaml, strip_markdown_fences


def test_strip_markdown_fences():
    text = "```yaml\nalias: Test\ntrigger: []\naction: []\n```"
    assert strip_markdown_fences(text).startswith("alias:")


def test_extract_llm_payload_text_from_json_wrapper():
    text = '{"yaml": "alias: Test\\ntrigger: []\\naction: []"}'
    assert extract_llm_payload_text(text).startswith("alias:")


def test_extract_llm_payload_text_from_markdown_content_field():
    text = '{"choices":[{"message":{"content":"```yaml\\nalias: Test\\ntrigger: []\\naction: []\\n```"}}]}'
    assert extract_llm_payload_text(text).startswith("alias:")


def test_parse_yaml_nested_trigger_action():
    text = """
alias: Test
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
"""
    data = parse_yaml(text)
    assert data["trigger"][0]["platform"] == "state"
    assert data["action"][0]["target"]["entity_id"] == "light.kitchen"
