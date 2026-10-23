import base64
import os
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DB_NAME = "vault.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    """Initializes tables for master settings and stored credentials."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Stores master password hash and encryption salt
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS master_config (
                id INTEGER PRIMARY KEY,
                master_hash TEXT NOT NULL,
                salt BLOB NOT NULL
            )
        """
        )
        # Stores credentials with encrypted passwords
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password TEXT NOT NULL
            )
        """
        )
        conn.commit()


def hash_password(password: str, salt: bytes) -> str:
    """Hashes a password with salt using SHA-256 for secure verification."""
    digest = hashes.Hash(hashes.SHA256())
    digest.update(salt + password.encode())
    return digest.finalize().hex()


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derives a Fernet encryption key from the master password."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def is_master_set() -> bool:
    """Checks whether the user has created a master password."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM master_config WHERE id = 1")
        return cursor.fetchone() is not None


def setup_master_password(password: str):
    """Saves the initial master password hash and salt."""
    salt = os.urandom(16)
    hashed = hash_password(password, salt)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO master_config (id, master_hash, salt) VALUES (1, ?, ?)",
            (hashed, salt),
        )
        conn.commit()


def verify_master_password(password: str):
    """
    Verifies master password.
    Returns (True, cipher_suite) if valid, otherwise (False, None).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT master_hash, salt FROM master_config WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return False, None

        stored_hash, salt = row
        if hash_password(password, salt) == stored_hash:
            key = derive_key(password, salt)
            return True, Fernet(key)
        return False, None


def add_credential(cipher: Fernet, service: str, username: str, password: str):
    encrypted = cipher.encrypt(password.encode()).decode()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO credentials (service, username, encrypted_password) VALUES (?, ?, ?)",
            (service, username, encrypted),
        )
        conn.commit()


def get_all_credentials(cipher: Fernet):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, service, username, encrypted_password FROM credentials")
        rows = cursor.fetchall()

    decrypted_list = []
    for item_id, service, username, enc_pass in rows:
        try:
            plain_pass = cipher.decrypt(enc_pass.encode()).decode()
        except Exception:
            plain_pass = "[Decryption Error]"
        decrypted_list.append((item_id, service, username, plain_pass))
    return decrypted_list


def delete_credential(item_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credentials WHERE id = ?", (item_id,))
        conn.commit()