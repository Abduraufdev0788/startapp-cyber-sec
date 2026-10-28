"""
Unit tests for Telegram account session encryption, phone number hashing, and authentication contracts.
"""

import uuid

import pytest

from app.core.exceptions import CryptographicException
from app.core.security import decrypt_field, encrypt_field, hash_phone_number


def test_telegram_session_encryption_with_user_aad():
    """Verifies that Telethon StringSession is encrypted with user_id as AAD."""
    user_id = uuid.uuid4()
    dummy_session = "1BAPxXXXXXXXXXX_mock_telethon_session_string_content_for_testing"

    # Encrypt
    encrypted_envelope = encrypt_field(
        plaintext=dummy_session,
        associated_data=str(user_id),
    )
    assert isinstance(encrypted_envelope, bytes)

    # Decrypt with correct user_id
    decrypted = decrypt_field(
        envelope=encrypted_envelope,
        associated_data=str(user_id),
    )
    assert decrypted.decode("utf-8") == dummy_session

    # Attempt decrypt with different user_id (Tenant isolation verification)
    other_user_id = uuid.uuid4()
    with pytest.raises(CryptographicException):
        decrypt_field(
            envelope=encrypted_envelope,
            associated_data=str(other_user_id),
        )


def test_phone_number_cleaning_and_hashing():
    """Verifies phone number normalization and deterministic hashing."""
    raw_phone_1 = "+998 90 123 45 67"
    raw_phone_2 = "+998901234567"

    hash_1 = hash_phone_number(raw_phone_1)
    hash_2 = hash_phone_number(raw_phone_2)

    assert hash_1 == hash_2
    assert len(hash_1) == 64
