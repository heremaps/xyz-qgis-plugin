import base64
from itertools import cycle

CRYPTER_STRING = "7JC1bRsq_4UCTZZkoRO5_zEtd48P1lvTvA9xlI_T8WqilSU5FXS51gEawfvsIKvIinE"


def encrypt_text(text):
    return xor_crypt_string(text, key=CRYPTER_STRING, encode=True)


def decrypt_text(text):
    return xor_crypt_string(text, key=CRYPTER_STRING, decode=True)


def xor_crypt_string(data: str, key="xor_string", encode=False, decode=False):
    bdata = data.encode("utf-8") if isinstance(data, str) else data
    if decode:
        bdata = base64.b64decode(bdata)
    xored = bytes(x ^ y for x, y in zip(bdata, cycle(key.encode("utf-8"))))
    out = xored
    if encode:
        out = base64.b64encode(xored)
    return out.decode("utf-8").strip()
