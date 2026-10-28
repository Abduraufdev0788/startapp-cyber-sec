"""
Cryptographic security primitives.
Implements:
1. AES-256-GCM authenticated envelope encryption for Telethon sessions & sensitive fields.
2. Associated Authenticated Data (AAD) binding to prevent cross-row copy-paste attacks.
3. Argon2id password hashing.
4. JWT token generation & verification.
5. Keyed HMAC-SHA256 for deterministic privacy-preserving lookups (e.g. phone numbers).
"""

import hmac
import os
import struct
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings
from app.core.exceptions import AuthenticationException, CryptographicException

# Envelope constants
ENVELOPE_VERSION = 1  # 1 byte
NONCE_LENGTH = 12     # 12 bytes standard for GCM
KEY_ID_FORMAT = "!I"  # 4 bytes big-endian unsigned int
HEADER_LENGTH = 1 + struct.calcsize(KEY_ID_FORMAT) + NONCE_LENGTH  # 1 + 4 + 12 = 17 bytes

password_hasher = PasswordHasher()


# ==============================================================================
# AES-256-GCM Envelope Encryption
# ==============================================================================

def encrypt_field(
    plaintext: bytes | str,
    key: bytes | None = None,
    key_id: int = 1,
    associated_data: bytes | str | None = None,
) -> bytes:
    """
    Encrypts sensitive data using AES-256-GCM with a versioned envelope format:
    [Version (1B)] || [KeyID (4B)] || [Nonce (12B)] || [Ciphertext + AuthTag (NB)]
    """
    if key is None:
        key = get_settings().master_key_bytes

    if len(key) != 32:
        raise CryptographicException("Encryption key must be exactly 32 bytes for AES-256.")

    data_bytes = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext
    aad_bytes = associated_data.encode("utf-8") if isinstance(associated_data, str) else associated_data

    # Generate a cryptographically secure 12-byte nonce (NEVER reuse)
    nonce = os.urandom(NONCE_LENGTH)
    aesgcm = AESGCM(key)

    try:
        # AESGCM.encrypt appends the 16-byte authentication tag to the ciphertext
        ciphertext_with_tag = aesgcm.encrypt(nonce, data_bytes, aad_bytes)
    except Exception as e:
        raise CryptographicException(f"Encryption failed: {e}") from e

    # Build the binary envelope
    header = struct.pack(f"!B{KEY_ID_FORMAT[1:]}", ENVELOPE_VERSION, key_id) + nonce
    return header + ciphertext_with_tag


def decrypt_field(
    envelope: bytes,
    keys: dict[int, bytes] | bytes | None = None,
    associated_data: bytes | str | None = None,
) -> bytes:
    """
    Decrypts an AES-256-GCM envelope, verifying authentication tag and AAD.
    Supports key rotation via key_id lookup.
    """
    if len(envelope) < HEADER_LENGTH + 16:
        raise CryptographicException("Ciphertext envelope is truncated or corrupted.")

    # Parse envelope header
    version, key_id = struct.unpack_from(f"!B{KEY_ID_FORMAT[1:]}", envelope, 0)
    if version != ENVELOPE_VERSION:
        raise CryptographicException(f"Unsupported envelope version: {version}")

    nonce = envelope[5:HEADER_LENGTH]
    ciphertext_with_tag = envelope[HEADER_LENGTH:]

    # Resolve decryption key
    if keys is None:
        key = get_settings().master_key_bytes
    elif isinstance(keys, dict):
        if key_id not in keys:
            raise CryptographicException(f"Decryption key ID {key_id} not available.")
        key = keys[key_id]
    else:
        key = keys

    aad_bytes = associated_data.encode("utf-8") if isinstance(associated_data, str) else associated_data
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, aad_bytes)
        return plaintext
    except InvalidTag as e:
        raise CryptographicException(
            "Authentication tag mismatch! Data has been modified, tampered with, or AAD is invalid."
        ) from e
    except Exception as e:
        raise CryptographicException(f"Decryption failed: {e}") from e


# ==============================================================================
# Password Hashing (Argon2id)
# ==============================================================================

def hash_password(password: str) -> str:
    """Hashes a password securely using Argon2id."""
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain password against an Argon2id hash."""
    try:
        return password_hasher.verify(hashed_password, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ==============================================================================
# JWT Authentication Tokens
# ==============================================================================

def create_access_token(
    subject: str,
    role: str = "USER",
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a signed JWT access token."""
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    role: str = "USER",
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a signed JWT refresh token."""
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT access token signature, type, and expiration."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") and payload.get("type") != "access":
            raise AuthenticationException("Invalid token type. Expected access token.", code="INVALID_TOKEN_TYPE")
        return payload
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationException("Access token has expired.", code="TOKEN_EXPIRED") from e
    except jwt.PyJWTError as e:
        raise AuthenticationException("Invalid access token.", code="INVALID_TOKEN") from e


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT refresh token signature, type, and expiration."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise AuthenticationException("Invalid token type. Expected refresh token.", code="INVALID_TOKEN_TYPE")
        return payload
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationException("Refresh token has expired.", code="TOKEN_EXPIRED") from e
    except jwt.PyJWTError as e:
        raise AuthenticationException("Invalid refresh token.", code="INVALID_TOKEN") from e


# ==============================================================================
# Deterministic Keyed Hashes (HMAC-SHA256)
# ==============================================================================

def hash_phone_number(phone: str, key: bytes | None = None) -> str:
    """
    Computes a keyed HMAC-SHA256 for phone numbers to enable deterministic lookup
    without storing raw phone numbers.
    """
    if key is None:
        key = get_settings().master_key_bytes
    normalized_phone = phone.strip().replace(" ", "").replace("-", "")
    return hmac.new(key, normalized_phone.encode("utf-8"), sha256).hexdigest()
