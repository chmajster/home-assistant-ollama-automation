"""Error types for integration."""

class LlmAutomationError(Exception):
    """Base integration error."""


class ProviderConnectionError(LlmAutomationError):
    """Raised when a provider connection fails."""


class ModelUnavailableError(LlmAutomationError):
    """Raised when selected model is unavailable."""


class YamlValidationError(LlmAutomationError):
    """Raised when YAML validation fails."""
