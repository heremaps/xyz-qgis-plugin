# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

import os

from XYZHubConnector.xyz_qgis.common.crypter import (
    xor_crypt_string,
    decrypt_text,
    encrypt_text,
)
from XYZHubConnector.xyz_qgis.iml.network.platform_server import PlatformServer, PlatformEndpoint

try:
    from test.utils import BaseTestAsync as TestCase, unittest
except ImportError:
    import unittest
    from unittest import TestCase


# decorator
def debug_test_function(func):
    return unittest.skipUnless(os.environ.get("DEBUG_TEST"), "Skipping debug test function")(func)


class TestCrypter(TestCase):
    def test_crypter(self):
        from secrets import token_urlsafe

        for i in range(10):
            with self.subTest(i=i):
                key = token_urlsafe(5)
                text = "https://example.com/example-a"
                enc = xor_crypt_string(text, key=key, encode=True)
                dec = xor_crypt_string(enc, key=key, decode=True)
                self.assertEqual(text, dec, "decrypted text does not match input text")

    def test_decrypt_platform_servers(self):
        for server_name in filter(str.isupper, vars(PlatformServer)):
            if "PRD" in server_name:
                continue
            value = getattr(PlatformServer, server_name)
            self.subtest_decrypt_value(server_name, value, "^https://.*")

    def test_decrypt_platform_endpoints(self):
        for name in filter(str.isupper, vars(PlatformEndpoint)):
            value = getattr(PlatformEndpoint, name)
            self.subtest_decrypt_value(name, value, "^/api")

    def subtest_decrypt_value(self, name, encoded, regex_pat):
        with self.subTest(name=name):
            self.assertNotRegex(encoded, regex_pat, "commited text should be encoded")
            text = decrypt_text(encoded)
            self.assertRegex(text, regex_pat)
            # print(name, text)

    @debug_test_function
    def test_encrypt_platform_servers(self):
        for name in filter(str.isupper, vars(PlatformServer)):
            url = getattr(PlatformServer, name)
            if not url.startswith("https://"):
                continue
            encoded = encrypt_text(url)
            print(name, encoded)

    @debug_test_function
    def test_encrypt_platform_endpoint(self):
        for name in filter(str.isupper, vars(PlatformEndpoint)):
            endpoint = getattr(PlatformEndpoint, name)
            if not endpoint.startswith("/api"):
                continue
            encoded = encrypt_text(endpoint)
            print(name, encoded)

    def test_encrypt_string(self):
        for text in os.environ.get("TEXT_TO_ENCRYPT", "example").split(","):
            print(text, encrypt_text(text))

    def test_decrypt_string(self):
        for text in os.environ.get("TEXT_TO_DECRYPT", "UjIiXBI+Fg==").split(","):
            print(text, decrypt_text(text))


if __name__ == "__main__":
    unittest.main()
    # unittest.main(defaultTest=["TestCrypter.test_encrypt_platform_servers"])
