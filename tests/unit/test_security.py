"""
Unit tests for core cryptographic primitives (AES-256-GCM, Argon2id, JWT, HMAC).
"""

import pytest

from app.core.exceptions import CryptographicException
from app.core.security import (
    create_access_token,
    decode_access_token,
    decrypt_field,
    encrypt_field,
    hash_password,
    hash_phone_number,
    verify_password,
)

# Test 32-byte key
TEST_KEY = bytes.fromhex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")


def test_aes_gcm_encryption_and_decryption_success():
    """Verifies that plaintext is encrypted into an envelope and decrypted accurately."""
    secret_data = "12345:telethon_session_string_content_test"
    aad = "user_account_uuid_1234"

    # Encrypt
    envelope = encrypt_field(
        plaintext=secret_data,
        key=TEST_KEY,
        key_id=1,
        associated_data=aad,
    )
    assert isinstance(envelope, bytes)
    assert len(envelope) > 17  # Header (17 bytes) + ciphertext + 16 bytes tag

    # Decrypt
    decrypted = decrypt_field(
        envelope=envelope,
        keys=TEST_KEY,
        associated_data=aad,
    )
    assert decrypted.decode("utf-8") == secret_data


def test_aes_gcm_tampering_rejection():
    """Verifies that modifying even a single byte of ciphertext causes decryption to fail."""
    secret_data = "sensitive_session_data"
    envelope = encrypt_field(plaintext=secret_data, key=TEST_KEY)

    # Tamper with the last byte of the envelope (the auth tag)
    tampered_envelope = bytearray(envelope)
    tampered_envelope[-1] ^= 0xFF

    with pytest.raises(CryptographicException, match="Authentication tag mismatch"):
        decrypt_field(envelope=bytes(tampered_envelope), keys=TEST_KEY)


def test_aes_gcm_aad_mismatch_rejection():
    """Verifies that attempting to decrypt with incorrect Associated Authenticated Data fails."""
    secret_data = "confidential_account_info"
    envelope = encrypt_field(plaintext=secret_data, key=TEST_KEY, associated_data="account_A")

    # Attempt to decrypt bound to account_B (Copy-Paste attack prevention)
    with pytest.raises(CryptographicException, match="Authentication tag mismatch"):
        decrypt_field(envelope=envelope, keys=TEST_KEY, associated_data="account_B")


def test_argon2id_password_hashing():
    """Verifies Argon2id password hashing and verification."""
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_flow():
    """Verifies JWT access token generation and decoding."""
    user_id = "test-user-uuid-1234"
    role = "ANALYST"

    token = create_access_token(subject=user_id, role=role)
    payload = decode_access_token(token)

    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert "exp" in payload


def test_jwt_refresh_token_flow():
    """Verifies JWT refresh token generation, validation, and type separation."""
    from app.core.exceptions import AuthenticationException
    from app.core.security import create_refresh_token, decode_refresh_token

    user_id = "test-user-uuid-5678"
    refresh_token = create_refresh_token(subject=user_id, role="USER")
    payload = decode_refresh_token(refresh_token)

    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"

    # Access token decoder must reject refresh token
    with pytest.raises(AuthenticationException):
        decode_access_token(refresh_token)

    # Refresh token decoder must reject access token
    access_token = create_access_token(subject=user_id)
    with pytest.raises(AuthenticationException):
        decode_refresh_token(access_token)


def test_phone_number_hmac():
    """Verifies deterministic keyed HMAC calculation for phone numbers."""
    phone = "+998 90 123 45 67"
    hashed_1 = hash_phone_number(phone, key=TEST_KEY)
    hashed_2 = hash_phone_number("+998901234567", key=TEST_KEY)

    assert hashed_1 == hashed_2
    assert len(hashed_1) == 64  # SHA-256 hex length
