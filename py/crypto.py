# -*- coding: utf-8 -*-
#  www.runcode.ru
#  Project:DOA_1.00 |  Scripts:crypto | Author:RUNCODE | Date: 03.05.2019
#  ----------------------------------------------------------------
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def encode(password, user):
    f = Fernet(base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'abcd', iterations=1000,
                                                   backend=default_backend()).derive(user.encode())))
    return f.encrypt(password.encode()).decode()


def decode(key, user):
    f = Fernet(base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'abcd', iterations=1000,
                                                   backend=default_backend()).derive(user.encode())))
    return f.decrypt(key.encode()).decode()