class EnvironmentError(Exception):
    """Base exception for environment variable errors."""
    pass


class ValidationError(EnvironmentError):
    """Raised when validation fails."""

    pass


class CastingError(EnvironmentError):
    """Raised when type casting fails."""
    pass
