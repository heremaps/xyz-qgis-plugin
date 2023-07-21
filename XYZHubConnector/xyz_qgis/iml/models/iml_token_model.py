# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from ...models import API_TYPES, SpaceConnectionInfo
from ...models.token_model import TokenModel, ServerTokenConfig, ComboBoxProxyModel


def get_api_type(server):
    return (
        API_TYPES.PLATFORM if server.lower().startswith(API_TYPES.PLATFORM) else API_TYPES.DATAHUB
    )


class IMLTokenModel(TokenModel):
    """Grouped Token Model, Cached changes and write to file at the end"""

    INFO_KEYS = ["name", "token", "user_login", "realm"]
    SERIALIZE_KEYS = ["token", "name", "user_login", "realm"]
    TOKEN_KEY = "token"

    def get_api_type(self):
        server = self.get_server()
        return get_api_type(server)

    def _validate_data(self, data):
        return data and (data.get(self.TOKEN_KEY) or data.get("user_login"))

    # default user login

    def set_server(self, *a, **kw):
        super().set_server(*a, **kw)
        cfg = self.to_dict()
        server = self.get_server()
        self._init_default_user_login(cfg, server)
        self.parser.update_config({server: cfg.get(server)})
        self.parser.write_to_file()
        self._refresh_model()

    def _init_default_user_login(self, cfg: dict, server_url):
        # server_url = server_info.get("token", "")
        if not server_url.startswith("PLATFORM"):
            return
        lst_data = cfg.setdefault(server_url, list())
        existing_user_logins = [data for data in lst_data if data.get("user_login")]
        if not existing_user_logins:
            server_name = SpaceConnectionInfo.platform_server_name(server_url)
            default_user_login = dict(
                name="{server} User Login".format(server=server_name),
                user_login="user_login",
            )
            lst_data.insert(0, default_user_login)


class IMLServerTokenConfig(ServerTokenConfig):
    def get_token_model(self):
        model = IMLTokenModel(self.ini, self.parser, self.parent)
        model.load_from_file()
        model.set_default_servers(self.default_api_urls)
        return model


class IMLComboBoxProxyModel(ComboBoxProxyModel):
    def __init__(self, token_key="token", named_token="{name}", nonamed_token="<noname token>"):
        ComboBoxProxyModel.__init__(
            self, token_key, named_token=named_token, nonamed_token=nonamed_token
        )

    def get_token(self, row):
        api_type = self.sourceModel().get_api_type()
        return "" if api_type == API_TYPES.PLATFORM else super().get_token(row)

    def get_here_credentials(self, row):
        api_type = self.sourceModel().get_api_type()
        if api_type == API_TYPES.PLATFORM:
            it = self.sourceModel().item(row, self.col_token)
            return it.text().strip() if it else ""
        else:
            return ""

    def get_user_login(self, row):
        return self.get_value_from_key("user_login", row)

    def get_realm(self, row):
        return self.get_value_from_key("realm", row)
