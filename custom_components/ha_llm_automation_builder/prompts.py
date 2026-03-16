"""Prompt templates and defaults."""

from __future__ import annotations

PROMPT_TEMPLATES: dict[str, str] = {
    "swiatla": "Skup się na automatyzacji świateł. Użyj bezpiecznych domyślnych godzin i warunków.",
    "alarm": "Utwórz konserwatywną automatyzację alarmu bez ryzykownych akcji.",
    "obecnosc": "Uwzględnij logikę obecności i osoby/device_tracker.",
    "ogrzewanie": "Twórz automatyzacje climate z histerezą i oszczędnym trybem.",
    "rolety": "Twórz automatyzacje cover na podstawie pory dnia i bezpieczeństwa.",
    "powiadomienia": "Twórz notyfikacje z czytelnymi komunikatami i warunkami antyspamowymi.",
}

SAFE_YAML_RULES = (
    "Return Home Assistant automation YAML only. No markdown fences. "
    "No comments outside explanation field. If uncertain entity exists, add warning. "
    "Do not invent entities. Preserve existing trigger/condition/action unless prompt explicitly changes them."
)
