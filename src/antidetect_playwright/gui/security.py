"""Security utilities for sensitive data handling."""

import base64
import hashlib
import os
import logging
import re
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecurePasswordEncryption:
    """Cryptographically secure password encryption using Fernet (AES-128).

    Uses PBKDF2 key derivation for additional security.
    Key is stored in environment variable or generated once and saved.
    """

    _KEY_ENV = "ANTIDETECT_ENCRYPTION_KEY"
    _KEY_FILE = ".encryption_key"
    _SALT = b"antidetect_salt_v1"  # Should be unique per installation in production

    @classmethod
    def _get_or_create_key(cls) -> bytes:
        """Get encryption key from env, file, or generate new one."""
        # Try environment variable first
        env_key = os.environ.get(cls._KEY_ENV)
        if env_key:
            try:
                # Validate it's a valid Fernet key
                key_bytes = env_key.encode()
                Fernet(key_bytes)  # Will raise if invalid
                return key_bytes
            except Exception as e:
                logger.warning(f"Invalid encryption key in environment: {e}")

        # Try key file
        key_file = Path.home() / cls._KEY_FILE
        if key_file.exists():
            try:
                key_bytes = key_file.read_bytes().strip()
                Fernet(key_bytes)  # Validate
                return key_bytes
            except Exception as e:
                logger.warning(f"Invalid encryption key in file: {e}")

        # Generate new key using PBKDF2
        logger.info("Generating new encryption key")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=cls._SALT,
            iterations=100000,
        )
        password = Fernet.generate_key()  # Random password
        derived_key = base64.urlsafe_b64encode(kdf.derive(password))

        # Save to file
        try:
            key_file.write_bytes(derived_key)
            # Set restrictive permissions (POSIX only)
            try:
                import stat
                import sys

                if sys.platform != 'win32':
                    # Unix/Linux/macOS: owner read/write only
                    key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
                else:
                    # Windows: use icacls for restrictive ACL
                    import subprocess
                    try:
                        # Remove inheritance and grant access only to current user
                        subprocess.run(
                            ['icacls', str(key_file), '/inheritance:r', '/grant:r',
                             f'{os.environ.get("USERNAME", "CURRENT_USER")}:F'],
                            capture_output=True,
                            check=False  # Don't fail if icacls unavailable
                        )
                    except (FileNotFoundError, subprocess.SubprocessError):
                        # icacls not available, skip permission setting
                        logger.warning("icacls not available on Windows, key file permissions not restricted")
            except Exception as perm_error:
                logger.warning(f"Could not set restrictive permissions on key file: {perm_error}")

            logger.info(f"Encryption key saved to {key_file}")
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")

        return derived_key

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Encrypt password for secure storage.

        Args:
            plaintext: Password to encrypt

        Returns:
            Encrypted string (base64 encoded)

        Raises:
            ValueError: If encryption fails
        """
        if not plaintext:
            return ""

        try:
            key = cls._get_or_create_key()
            f = Fernet(key)
            encrypted = f.encrypt(plaintext.encode("utf-8"))
            return encrypted.decode("ascii")
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt password: {e}")

    @classmethod
    def decrypt(cls, encrypted: str) -> str:
        """Decrypt password from storage.

        Args:
            encrypted: Encrypted string

        Returns:
            Decrypted password

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted:
            return ""

        try:
            key = cls._get_or_create_key()
            f = Fernet(key)
            decrypted = f.decrypt(encrypted.encode("ascii"))
            return decrypted.decode("utf-8")
        except InvalidToken:
            # Try legacy XOR decryption for migration
            logger.warning("Attempting legacy XOR decryption")
            try:
                return cls._legacy_xor_decrypt(encrypted)
            except Exception:
                logger.error("Failed to decrypt with both Fernet and legacy XOR")
                raise ValueError(
                    "Failed to decrypt password - invalid key or corrupted data"
                )
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt password: {e}")

    @classmethod
    def _legacy_xor_decrypt(cls, encrypted: str) -> str:
        """Legacy XOR decryption for backward compatibility."""
        try:
            key_str = os.environ.get(
                "ANTIDETECT_LEGACY_KEY", "antidetect_local_obfuscation_key_v1"
            )
            key = hashlib.sha256(key_str.encode()).digest()
            encrypted_bytes = base64.b64decode(encrypted.encode("ascii"))
            decrypted = bytes(
                encrypted_bytes[i] ^ key[i % len(key)]
                for i in range(len(encrypted_bytes))
            )
            return decrypted.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Legacy decryption failed: {e}")


class SecureLogFilter(logging.Filter):
    """Filter sensitive data from log messages."""

    SENSITIVE_PATTERNS = [
        "password",
        "secret",
        "token",
        "api_key",
        "credential",
        "auth",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log record."""
        if hasattr(record, "msg") and record.msg:
            msg_lower = str(record.msg).lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in msg_lower:
                    # Check if args contain sensitive data
                    if record.args:
                        record.args = tuple(
                            self._redact_arg(arg) for arg in record.args
                        )
        return True

    def _redact_arg(self, arg) -> str:
        """Redact sensitive argument."""
        if isinstance(arg, dict):
            return self._redact_dict(arg)
        elif isinstance(arg, str):
            # If looks like it contains sensitive data
            if any(p in arg.lower() for p in self.SENSITIVE_PATTERNS):
                return "[REDACTED]"
        return arg

    def _redact_dict(self, d: dict) -> dict:
        """Redact sensitive keys from dict."""
        result = {}
        for key, value in d.items():
            key_lower = key.lower()
            if any(p in key_lower for p in self.SENSITIVE_PATTERNS):
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            else:
                result[key] = value
        return result


def install_secure_logging():
    """Install secure log filter on root logger."""
    root_logger = logging.getLogger()
    root_logger.addFilter(SecureLogFilter())


def validate_uuid(value: str) -> bool:
    """Validate that string is a valid UUID."""
    import re

    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))


def sanitize_path_component(value: str) -> str:
    """Sanitize string for use in file paths to prevent traversal attacks."""
    # Remove any path separators and dangerous characters
    sanitized = re.sub(r'[/\\:*?"<>|]', "", value)
    # Remove parent directory references
    sanitized = sanitized.replace("..", "")
    # Limit length
    return sanitized[:255]


# Backward compatibility alias
PasswordEncryption = SecurePasswordEncryption
