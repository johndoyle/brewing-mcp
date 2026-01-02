"""
Exception types for brewing-common.

All exceptions inherit from BrewingCommonError for easy catching
of any library-related errors.
"""


class BrewingCommonError(Exception):
    """Base exception for all brewing-common errors."""

    pass


class UnitConversionError(BrewingCommonError):
    """Raised when a unit conversion fails."""

    pass


class MatchingError(BrewingCommonError):
    """Raised when ingredient matching fails."""

    pass


class ValidationError(BrewingCommonError):
    """Raised when data validation fails."""

    pass


class ConfigurationError(BrewingCommonError):
    """Raised when configuration is invalid or missing."""

    pass


class ConnectionError(BrewingCommonError):
    """Raised when connection to an external service fails."""

    pass


class NotFoundError(BrewingCommonError):
    """Raised when a requested resource is not found."""

    pass


class PermissionError(BrewingCommonError):
    """Raised when access to a resource is denied."""

    pass
