# shared/encryption.py
# This module provides utilities for encrypting and decrypting sensitive data (PII)
# using the Fernet symmetric encryption scheme from the cryptography library.

from cryptography.fernet import Fernet
from flask import current_app  # To access the ENCRYPTION_KEY from Flask's app config
import base64  # For base64 encoding/decoding

_cipher_suite = None  # Global variable to store the Fernet cipher suite instance


def _get_cipher_suite() -> Fernet:
    """
    Lazily initializes and returns the Fernet cipher suite.
    The encryption key is retrieved from the Flask application's configuration.
    Raises:
        RuntimeError: If ENCRYPTION_KEY is not set in the Flask configuration.
        ValueError: If the provided ENCRYPTION_KEY is invalid for Fernet.
    """
    global _cipher_suite
    if _cipher_suite is None:
        # Get the encryption key from the Flask app's configuration.
        # This key should be a URL-safe base64-encoded 32-byte key.
        key = current_app.config.get('ENCRYPTION_KEY')
        if not key:
            raise RuntimeError("ENCRYPTION_KEY not set in Flask configuration. Cannot encrypt/decrypt.")

        try:
            # Initialize Fernet with the provided key.
            _cipher_suite = Fernet(key.encode('utf-8'))
        except Exception as e:
            # Catch errors during Fernet initialization (e.g., invalid key format).
            raise ValueError(f"Invalid ENCRYPTION_KEY. Must be a URL-safe base64-encoded 32-byte key: {e}")
    return _cipher_suite


def encrypt_data(data: str) -> bytes:
    """
    Encrypts a plain-text string using the configured Fernet cipher.
    Args:
        data (str): The string to be encrypted.
    Returns:
        bytes: The encrypted data as bytes.
    """
    cipher_suite = _get_cipher_suite()
    return cipher_suite.encrypt(data.encode('utf-8'))


def decrypt_data(encrypted_data: bytes) -> str:
    """
    Decrypts encrypted data (bytes) back into a plain-text string.
    Args:
        encrypted_data (bytes): The encrypted data to be decrypted.
    Returns:
        str: The decrypted data as a string.
    Raises:
        cryptography.fernet.InvalidToken: If the token is tampered with or invalid.
    """
    cipher_suite = _get_cipher_suite()
    return cipher_suite.decrypt(encrypted_data).decode('utf-8')

# --- Key Generation Example (for development setup) ---
# To generate a new Fernet key for your .env file, run this once:
# from cryptography.fernet import Fernet
# print(Fernet.generate_key().decode())
# Copy the output string into your .env file for ENCRYPTION_KEY.
