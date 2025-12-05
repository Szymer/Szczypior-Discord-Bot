"""Custom exceptions for Szczypior Discord Bot."""


class SzczypiorBotError(Exception):
    """Base exception for all bot-related errors."""


class ConfigurationError(SzczypiorBotError):
    """Raised when there's an error in configuration (missing keys, invalid values, etc.)."""


class LLMError(SzczypiorBotError):
    """Base exception for LLM-related errors."""


class LLMAnalysisError(LLMError):
    """Raised when LLM analysis fails (invalid response, timeout, etc.)."""


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""


class SheetsError(SzczypiorBotError):
    """Base exception for Google Sheets-related errors."""


class SheetsOperationError(SheetsError):
    """Raised when a Sheets operation fails (write, read, etc.)."""


class SheetsConnectionError(SheetsError):
    """Raised when connection to Google Sheets fails."""


class ActivityError(SzczypiorBotError):
    """Base exception for activity-related errors."""


class ActivityValidationError(ActivityError):
    """Raised when activity validation fails (invalid type, distance, etc.)."""


class DuplicateActivityError(ActivityError):
    """Raised when attempting to add a duplicate activity."""
