##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""This module provides PKCS#5 v2.0 Password-Based Key Derivation (PBKDF2)
algorithm for secure password hashing.
"""

import base64
import os

from AccessControl.AuthEncoding import registerScheme

from cryptography.hazmat.primitives import hashes, constant_time
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


# Default number of iterations to perform of the hash function.
DEFAULT_ITERATIONS_COUNT = 100000

DEFAULT_HASH_LEN = 24  # Default length of the generated hash.
DEFAULT_SALT_LEN = 24  # Default length of the random generated salt.


class PBKDF2DigestScheme:

    def encrypt(self, pw):
        """Encrypt the provided plain text password.

        Returns string in format:

            <iterations>$<base64_salt>$<base64_hash>
        """
        salt = _generate_salt(DEFAULT_SALT_LEN)
        iterations = DEFAULT_ITERATIONS_COUNT

        password_hash = _encrypt(pw, salt, iterations, DEFAULT_HASH_LEN)

        return '%s$%s$%s' % (iterations, base64.b64encode(salt),
                             base64.b64encode(password_hash))

    def validate(self, reference, attempt):
        """Validate the provided password string.

        Reference is the correct password, which may be encrypted; attempt is
        clear text password attempt.
        """
        try:
            iterations_str, salt_b64, password_hash_b64 = reference.split('$')

            iterations = int(iterations_str)
            salt = base64.b64decode(salt_b64)
            password_hash = base64.b64decode(password_hash_b64)
        except (ValueError, TypeError):
            return False

        if iterations <= 0:
            return False

        attempt_hash = _encrypt(attempt, salt, iterations, len(password_hash))

        return constant_time.bytes_eq(attempt_hash, password_hash)


def _generate_salt(salt_len):
    """Generates random string for salt."""
    return os.urandom(salt_len)


def _encrypt(password, salt, iterations, hash_len):
    """Performs key derivation according to the PKCS#5 standard (v2.0), by
    means of the PBKDF2 algorithm using HMAC-SHA256 as a pseudorandom
    function.
    """
    backend = default_backend()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=hash_len,
                     salt=salt, iterations=iterations, backend=backend)
    return kdf.derive(password)


registerScheme('PBKDF2-SHA256', PBKDF2DigestScheme())
