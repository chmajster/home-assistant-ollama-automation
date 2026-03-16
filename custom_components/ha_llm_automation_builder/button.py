"""Button platform for quick runtime actions."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROVIDER_OLLAMA
from .helpers.errors import LlmAutomationError, ModelUnavailableError


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TestConnectionButton(runtime),
            RefreshModelsButton(runtime),
            PullConfiguredModelButton(runtime),
            GenerateFromPromptButton(runtime),
        ]
    )


class BaseRuntimeButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime) -> None:
        super().__init__(runtime.coordinator)
        self.runtime = runtime

    def _notify(self, title: str, message: str) -> None:
        persistent_notification.async_create(
            self.hass,
            message,
            title=title,
            notification_id=f"{DOMAIN}_{self.__class__.__name__.lower()}",
        )


class TestConnectionButton(BaseRuntimeButton):
    _attr_name = "test_connection"

    async def async_press(self) -> None:
        model = self.runtime.config.get("model")
        try:
            conn = await self.runtime.adapter.test_connection()
            models = await self.runtime.adapter.list_models()
            model_ok = False
            if model:
                try:
                    await self.runtime.adapter.test_model(model)
                    model_ok = True
                except ModelUnavailableError:
                    model_ok = False
            self._notify(
                "LLM connection test",
                (
                    f"Connection OK: {bool(conn.get('ok'))}\n"
                    f"Configured model: {model or '-'} (ok: {model_ok})\n"
                    f"Available models: {len(models)}"
                ),
            )
        except LlmAutomationError as err:
            self._notify("LLM connection test", f"Connection failed: {err}")


class RefreshModelsButton(BaseRuntimeButton):
    _attr_name = "refresh_models"

    async def async_press(self) -> None:
        try:
            models = await self.runtime.adapter.list_models()
            preview = ", ".join(models[:10]) if models else "-"
            suffix = "" if len(models) <= 10 else " ..."
            self._notify(
                "LLM models",
                f"Models found: {len(models)}\n{preview}{suffix}",
            )
        except LlmAutomationError as err:
            self._notify("LLM models", f"Failed to load model list: {err}")


class PullConfiguredModelButton(BaseRuntimeButton):
    _attr_name = "pull_configured_model"

    async def async_press(self) -> None:
        if self.runtime.config.get("provider") != PROVIDER_OLLAMA:
            self._notify("LLM model pull", "Model pull is available only for provider=ollama.")
            return

        model = self.runtime.config.get("model")
        if not model:
            self._notify("LLM model pull", "Configured model is empty.")
            return

        try:
            await self.runtime.adapter.pull_model(model)
            models = await self.runtime.adapter.list_models()
            await self.runtime.coordinator.async_request_refresh()
            self._notify(
                "LLM model pull",
                f"Model downloaded: {model}\nAvailable models now: {len(models)}",
            )
        except LlmAutomationError as err:
            self._notify("LLM model pull", f"Model pull failed: {err}")


class GenerateFromPromptButton(BaseRuntimeButton):
    _attr_name = "generate_automation_from_prompt"

    async def async_press(self) -> None:
        description = (self.runtime.ui_prompt or "").strip()
        if not description:
            self._notify("Automation generation", "Prompt is empty. Fill the prompt text field first.")
            return

        try:
            result = await self.hass.services.async_call(
                DOMAIN,
                "generate_automation",
                {"description": description},
                blocking=True,
                return_response=True,
            )
        except TypeError:
            await self.hass.services.async_call(
                DOMAIN,
                "generate_automation",
                {"description": description},
                blocking=True,
            )
            result = self.runtime.last_result
        except HomeAssistantError as err:
            self._notify("Automation generation", f"Generation failed: {err}")
            return

        yaml_text = (result or {}).get("yaml", "")
        preview = yaml_text[:700] if yaml_text else "-"
        self._notify("Automation generation", f"Generated YAML preview:\n{preview}")
