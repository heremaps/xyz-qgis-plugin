# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from os.path import exists, expanduser, expandvars

from .utils import read_properties_file


class HereCredentials:
    def __init__(
        self,
        user: str,
        client: str,
        key: str,
        secret: str,
        endpoint: str = "https://account.api.here.com/oauth2/token",
        cred_type: str = "DEFAULT",
        token_properties: dict = None,
    ):
        """
        Instantiate the credentials object.

        :param user: the HERE user id
        :param client: the HERE client id
        :param key: the HERE access key id
        :param secret: there HERE access key secret
        :param endpoint: the URL of the HERE account service
        :param cred_type: the type of credentials eg: DEFAULT, TOKEN
        :token_path: the path of the token file
        :token_properties: the properties of a token as a dict
        """
        self.user = user
        self.client = client
        self.key = key
        self.secret = secret
        self.endpoint = endpoint
        self.cred_type = cred_type
        self.token_properties = token_properties

    @classmethod
    def from_file(cls, path: str) -> "HereCredentials":
        """
        Return the credentials from a specified path.credentials.

        :param path: path to a HERE platform credentials.properties file.
        :return: credentials
        :raises HereCredentialsException: Unable to find credentials file in path
        """
        credentials_path = expanduser(expandvars(path))

        if not exists(credentials_path):
            raise HereCredentialsException(
                "Unable to find credentials file in path {}".format(path)
            )

        credentials_properties = read_properties_file(credentials_path)

        try:
            user = credentials_properties.get("here.user.id", "")
            client = credentials_properties["here.client.id"]
            key = credentials_properties["here.access.key.id"]
            secret = credentials_properties["here.access.key.secret"]
            endpoint = credentials_properties["here.token.endpoint.url"]
        except KeyError:
            raise HereCredentialsException("Erroneous credential property file")

        return cls(user, client, key, secret, endpoint)


class HereCredentialsException(Exception):
    """
    This ``HereCredentialsException`` is raised when the HERE platform credentials are
    not accepted.
    """
