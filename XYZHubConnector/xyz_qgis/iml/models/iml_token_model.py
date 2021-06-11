# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from ...models import API_TYPES
from ...models.token_model import TokenModel, ServerTokenConfig, ComboBoxProxyModel


def get_api_type(server):
    return (
        API_TYPES.PLATFORM if server.lower().startswith(API_TYPES.PLATFORM) else API_TYPES.DATAHUB
    )


class IMLTokenModel(TokenModel):
    """Grouped Token Model, Cached changes and write to file at the end"""

    def get_api_type(self):
        server = self.get_server()
        return get_api_type(server)


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
