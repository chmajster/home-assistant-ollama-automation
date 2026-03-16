from custom_components.ha_llm_automation_builder.helpers.yaml_tools import strip_markdown_fences


def test_strip_markdown_fences():
    text = "```yaml\nalias: Test\ntrigger: []\naction: []\n```"
    assert strip_markdown_fences(text).startswith("alias:")
