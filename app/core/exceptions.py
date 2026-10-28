"""
Custom application exception hierarchy.
Enforces consistent error codes, user-friendly messages, and HTTP status mapping.
"""

from typing import Any


class AppException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


# ------------------------------------------------------------------------------
# Security & Authentication Exceptions
# ------------------------------------------------------------------------------
class CryptographicException(AppException):
    """Raised when an encryption, decryption, or authentication tag verification fails."""

    def __init__(self, message: str = "Cryptographic operation failed.") -> None:
        super().__init__(
            message=message,
            code="CRYPTOGRAPHIC_ERROR",
            status_code=500,
        )


class SSRFBlockedException(AppException):
    """Raised when an untrusted URL targets a reserved, loopback, or private network."""

    def __init__(
        self,
        message: str = "The target URL resolves to a private, loopback, or prohibited network.",
        target_ip: str | None = None,
    ) -> None:
        details = [{"target_ip": target_ip}] if target_ip else []
        super().__init__(
            message=message,
            code="SSRF_ATTEMPT_BLOCKED",
            status_code=400,
            details=details,
        )


class AuthenticationException(AppException):
    """Raised when credentials or tokens are invalid."""

    def __init__(self, message: str = "Authentication failed.", code: str = "UNAUTHORIZED") -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=401,
        )


class ForbiddenException(AppException):
    """Raised when the user does not have permission to access a resource."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
        )


class ResourceNotFoundException(AppException):
    """Raised when a requested resource is not found (or hidden for anti-IDOR)."""

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )


# ------------------------------------------------------------------------------
# Telegram Integration Exceptions
# ------------------------------------------------------------------------------
class TelegramFloodWaitException(AppException):
    """Raised when Telegram MTProto rate limits an action with FloodWait."""

    def __init__(self, seconds: int) -> None:
        super().__init__(
            message=f"Telegram rate limit reached. Please wait {seconds} seconds.",
            code="TELEGRAM_FLOOD_WAIT",
            status_code=429,
            details=[{"retry_after_seconds": seconds}],
        )
        self.seconds = seconds


class TelegramAuthException(AppException):
    """Raised when Telegram phone code or 2FA verification fails."""

    def __init__(self, message: str, code: str = "TELEGRAM_AUTH_ERROR") -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=400,
        )


class TelegramSessionRevokedException(AppException):
    """Raised when an active session has been revoked externally by the user."""

    def __init__(self, message: str = "Telegram session has been revoked.") -> None:
        super().__init__(
            message=message,
            code="SESSION_REVOKED",
            status_code=401,
        )


# ------------------------------------------------------------------------------
# Detection & AI Exceptions
# ------------------------------------------------------------------------------
class TargetUnreachableException(AppException):
    """Raised when the target website cannot be reached (DNS failure, network timeout)."""

    def __init__(self, message: str = "Target website could not be reached.") -> None:
        super().__init__(
            message=message,
            code="TARGET_UNREACHABLE",
            status_code=502,
        )


class AIProviderException(AppException):
    """Raised when the AI provider (Google Gemini) returns an error or times out."""

    def __init__(self, message: str = "AI service is currently unavailable.") -> None:
        super().__init__(
            message=message,
            code="AI_PROVIDER_ERROR",
            status_code=503,
        )
