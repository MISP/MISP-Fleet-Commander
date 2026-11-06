"""Encryption of the secrets stored in the database (MISP authkeys).

The key comes from the `MFC_ENCRYPTION_KEY` environment variable or, when it is not set, from a key file
(`MFC_ENCRYPTION_KEY_FILE`, by default next to the database). Without either, a key file is generated, unless
the database already holds encrypted values: those can only be read with the key that encrypted them.

Several keys can be given, newest first, separated by commas or newlines. The first one encrypts, all of them
decrypt: this is how keys are rotated (see `flask security rotate-key`).
"""
import os
import re
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

_cipher = None


class EncryptionKeyError(RuntimeError):
    pass


def generateKey() -> str:
    return Fernet.generate_key().decode()


def parseKeys(raw) -> list:
    return [key for key in re.split(r'[\s,]+', raw or '') if key]


def buildCipher(keys: list) -> MultiFernet:
    if not keys:
        raise EncryptionKeyError('No encryption key configured')
    try:
        return MultiFernet([Fernet(key) for key in keys])
    except (ValueError, TypeError):
        raise EncryptionKeyError('The encryption key is malformed: expected url-safe base64 encoded 32-byte keys, '
                                 'as printed by `flask security generate-key`')


def readKeyFile(path: Path) -> list:
    try:
        return parseKeys(path.read_text())
    except FileNotFoundError:
        return []


def createSecretFile(path: Path, secret: str) -> None:
    """Write a secret to a new file readable by its owner only. If the file already exists, it is kept: concurrent
    processes end up sharing the same secret."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, 'w') as secretFile:
        secretFile.write(secret + '\n')


def createKeyFile(path: Path) -> list:
    createSecretFile(path, generateKey())
    return readKeyFile(path)


def readOrCreateSecretKey(path: Path) -> str:
    """The secret signing the session tokens, generated on first use"""
    createSecretFile(path, secrets.token_hex(32))
    secret = path.read_text().strip()
    if not secret:
        raise EncryptionKeyError(f'The secret key file {path} is empty')
    return secret


def init(app, hasEncryptedData) -> None:
    """Load the encryption key, generating one on new installs, then check it opens the stored secrets.
    `hasEncryptedData` returns a sample encrypted value from the database, or None if there is none."""
    global _cipher
    keyFile = Path(app.config['ENCRYPTION_KEY_FILE'])
    keys = parseKeys(app.config.get('ENCRYPTION_KEY'))
    source = 'MFC_ENCRYPTION_KEY'
    if not keys:
        keys = readKeyFile(keyFile)
        source = str(keyFile)
    sample = hasEncryptedData()
    if not keys:
        if sample is not None:
            raise EncryptionKeyError(
                'The database contains encrypted MISP authkeys but no encryption key is configured. '
                f'Restore the key from your backups into MFC_ENCRYPTION_KEY or {keyFile}.')
        keys = createKeyFile(keyFile)
        app.logger.warning(f'Generated a new encryption key in {keyFile}. Back it up: '
                           'the MISP authkeys stored in the database cannot be read without it.')
    _cipher = buildCipher(keys)
    if sample is not None:
        try:
            _cipher.decrypt(sample.encode())
        except InvalidToken:
            raise EncryptionKeyError(
                f'The encryption key from {source} does not decrypt the MISP authkeys stored in the database. '
                'Configure the key that encrypted them.')


def cipher() -> MultiFernet:
    if _cipher is None:
        raise EncryptionKeyError('The encryption key is not loaded')
    return _cipher


def encrypt(value):
    if value is None:
        return None
    return cipher().encrypt(value.encode()).decode()


def decrypt(token):
    if token is None:
        return None
    try:
        return cipher().decrypt(token.encode()).decode()
    except InvalidToken:
        raise EncryptionKeyError('A stored secret cannot be decrypted with the configured encryption keys')


def rotate(token):
    """Re-encrypt a value with the first configured key"""
    if token is None:
        return None
    try:
        return cipher().rotate(token.encode()).decode()
    except InvalidToken:
        raise EncryptionKeyError('A stored secret cannot be decrypted with the configured encryption keys')
