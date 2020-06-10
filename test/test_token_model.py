# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

import re
from test.utils import BaseTestAsync, TestFolder

from qgis.PyQt.QtGui import QStandardItem
from qgis.testing import unittest
from XYZHubConnector.xyz_qgis.models.token_model import (
    ConfigParserMixin, TokenModel,
    ServerModel, make_config_parser)


# import unittest
# class TestTokenModel(BaseTestAsync, unittest.TestCase):
class TestTokenModel(BaseTestAsync):
    def test_init_empty_ini(self):
        folder = TestFolder()
        folder.save("token.ini", "")
        ini = folder.fullpath("token.ini")
        token_model = TokenModel(ini)
        token_model.load_from_file()
        
        input_token_info = [dict(name="somename", token="helloworldtoken")]
        for token_info in input_token_info:
            token_model.appendRow([QStandardItem(t)  
                for t in token_model.items_from_data(token_info)
            ])
        token_model.submit_cache()
        txt = folder.load("token.ini")

        self.assertEqual('[PRD]\nhelloworldtoken,somename\n\n', txt.replace("\r\n","\n"), "ini does not match expected")

    def test_load_old_config(self):
        """ load old config should results in new config that is backward-compatible. 
        Expected output contains the old server env and the newly migrated server url
        """
        txt = "[PRD]\nA0\nA1,\nA2,A2\n\n[B]\nB0\n\n"

        folder = TestFolder()
        folder.save("token.ini", txt)
        ini = folder.fullpath("token.ini")
        token_model = TokenModel(ini)
        token_model.load_from_file()

        url = "https://hub-server-prd.com/hub"
        token_model.set_default_servers(dict(PRD=url))
        self.assertEqual({
            'PRD': [{'token': 'A0'}, {'token': 'A1', 'name': ''}, {'token': 'A2', 'name': 'A2'}],
            url: [{'token': 'A0'}, {'token': 'A1', 'name': ''}, {'token': 'A2', 'name': 'A2'}],
            'B': [{'token': 'B0'}], 
            },
            token_model.to_dict()
        )

        folder.save("token.ini", "")
        token_model.submit_cache()
        out = folder.load("token.ini")
        self.assertEqual(txt + "[{}]\nA0,\nA1,\nA2,A2\n\n".format(url),
            out.replace("\r\n","\n"), "ini does not match expected")

    def test_set_server(self):
        folder = TestFolder()
        folder.save("token.ini", "")
        ini = folder.fullpath("token.ini")
        token_model = TokenModel(ini)
        token_model.load_from_file()
        folder.save("token.ini", "")

        server_env_url = dict(PRD="https://hub-server-prd.com/hub",CIT="https://hub-server-cit.com/hub")
        token_model.set_default_servers(server_env_url)

        # load data via ui functions
        token_model.refresh_model()
        input_token_info = dict()
        for server, url in server_env_url.items():
            lst = [dict(name="token for {}".format(server), token="helloworldtoken")]
            input_token_info[url] = lst

            token_model.set_server(url)
            for token_info in lst:
                token_model.appendRow([QStandardItem(t)  
                    for t in token_model.items_from_data(token_info)
                ])
            token_model.submit_cache()

        self.assertMultiInput(
            input_token_info, 
            [
            token_model.to_dict(),
            token_model.parser.get_config()
            ],
        )
        out = folder.load("token.ini")
        self.assertEqual('[https://hub-server-prd.com/hub]\nhelloworldtoken,token for PRD\n\n[https://hub-server-cit.com/hub]\nhelloworldtoken,token for CIT\n\n',
            out.replace("\r\n","\n"), "ini does not match expected")

    def test_load_mixed_old_new_config(self):
        """ test loading config with both old server env and new server url. 
        Expected the old server env remains unchanged for backward-compatible, 
        the new server url got updated
        """
        url = "https://hub-server-prd.com/hub"
        txt = "[PRD]\nA0\nA1,\nA2,A2\n\n[{}]\nB0,\nB1,\n\n".format(url)

        folder = TestFolder()
        folder.save("token.ini", txt)
        ini = folder.fullpath("token.ini")
        token_model = TokenModel(ini)
        token_model.load_from_file()
        folder.save("token.ini", "")

        server_env_url = dict(PRD=url)
        token_model.set_default_servers(server_env_url)
        
        self.assertMultiInput(
            {
            'PRD': [{'token': 'A0'}, {'token': 'A1', 'name': ''}, {'token': 'A2', 'name': 'A2'}], 
            url: [{'token': 'B0', 'name': ''}, {'token': 'B1', 'name': ''}],
            },
            [
            token_model.to_dict(),
            token_model.parser.get_config()
            ],
        )
        
        token_model.set_server(url)
        token_model.appendRow([QStandardItem(t) 
            for t in token_model.items_from_data(dict(token="B2",name=""))])
        token_model.submit_cache()
        out = folder.load("token.ini")
        self.assertEqual(txt.replace("B1,","B1,\nB2,"), out.replace("\r\n","\n"), "ini does not match expected")

class TestConfigParserMixin(BaseTestAsync):
    def test_deserialize_token(self):
        parser = ConfigParserMixin("","", serialize_keys=("token","name"))
        self.assertMultiInput(
            dict(token="onlytoken"),
            [
                parser.deserialize("onlytoken"),
                parser.deserialize(" onlytoken"),
                parser.deserialize("onlytoken "),
                parser.deserialize("onlytoken \t"),
            ]
        )
        self.assertMultiInput(
            dict(token="onlytoken", name=""),
            [
            parser.deserialize("onlytoken,"),
            parser.deserialize("onlytoken , "),
            ],
        )
        self.assertMultiInput(
            dict(token="helloworldtoken", name="nameoftoken"),
            [
            parser.deserialize("helloworldtoken,nameoftoken"),
            parser.deserialize("helloworldtoken, nameoftoken"),
            parser.deserialize("helloworldtoken ,nameoftoken"),
            parser.deserialize(" helloworldtoken , nameoftoken "),
            ],
        )
        self.assertMultiInput(
            dict(token="helloworldtoken", name="name,with,comma"),
            [
            parser.deserialize("helloworldtoken,name,with,comma"),
            parser.deserialize("helloworldtoken, name,with,comma"),
            ],
        )
            
        self.assertEqual(
            dict(token="helloworldtoken", name="name,with space comma"),
            parser.deserialize("helloworldtoken,name,with space comma"),
        )

        self.assertEqual(
            dict(token="helloworldtoken", name="name,with space comma"),
            parser.deserialize("helloworldtoken,name,with space comma"),
        )
            
        self.assertEqual(
            dict(token="helloworldtoken", name="name,with, space comma"),
            parser.deserialize("helloworldtoken, name,with, space comma"),
        )

        self.assertEqual(
            dict(token="+*~#-.! = e23"),
            parser.deserialize("+*~#-.! = e23"), "deserialize special char failed"
        )
        self.assertEqual(
            dict(token=r"!\"#$%&'()*+-./:;<=>?@[\]^_`{|}~"),
            parser.deserialize(r"!\"#$%&'()*+-./:;<=>?@[\]^_`{|}~"), "deserialize special char failed"
        )

    def test_serialize_token(self):
        parser = ConfigParserMixin("","", serialize_keys=("token","name"))

        self.assertMultiInput(
            "helloworldtoken,name,with space comma",
            [
            parser.serialize_data(dict(token="helloworldtoken", name="name,with space comma")),
            parser.serialize_data(dict(token="helloworldtoken \t", name=" name,with space comma ")),
            ],
        )
            
        self.assertMultiInput(
            "helloworldtoken,",
            [
            parser.serialize_data(dict(token="helloworldtoken")),
            ],
        )
        self.assertMultiInput(
            ",namewithouttoken",
            [
            parser.serialize_data(dict(name="namewithouttoken")),
            ],
        )

    def test_update_config(self):
        parser = ConfigParserMixin("",make_config_parser(),serialize_keys=("token","name"))
        sections = ["A","B"]
        data = {s: [
            dict(token="{}{}".format(s,i), name="{}{}".format(s,i)) 
            for i in range(3)
            ]
            for s in sections
        }
        parser.update_config(dict(A=data["A"]))
        parser.update_config(dict(B=data["B"]))

        try:
            self.assertEqual(
                data,
                parser.get_config()
            )

            data["A"].reverse()
            self.assertNotEqual(
                data,
                parser.get_config()
            )

            parser.update_config(dict(A=data["A"]))
            self.assertEqual(
                data,
                parser.get_config()
            )

            data["B"].clear()
            self.assertNotEqual(
                data,
                parser.get_config()
            )

            parser.update_config(dict(B=data["B"]))
            self.assertEqual(
                data,
                parser.get_config()
            )
            
            data.update({s: [
                dict(token="{}{}".format(s,i), name="{}{}".format(s,i)) 
                for i in range(3)]
                for s in ["C"]
            })
            
            parser.update_config(dict(C=data["C"]))
            self.assertEqual(
                data,
                parser.get_config()
            )
            
            data_with_invalid_section = {s: [
                dict(token="{}{}".format(s,i), name="{}{}".format(s,i)) 
                for i in range(3)]
                for s in [" ",""]
            }
            parser.update_config(data_with_invalid_section)
            self.assertEqual(
                data,
                parser.get_config(), "data with invalid section is not rejected"
            )
            
            # # TODO: test invalid token in final token model
            # # writer does not know what is an invalid data (empty token or name)
            # # the token model should know
            # data_with_invalid_token = {s: [
            #     dict(token="", name="{}{}".format(s,i)) 
            #     for i in range(3)]
            #     for s in ["D"]
            # }
            # parser.update_config(data_with_invalid_token)
            # self.assertEqual(
            #     data,
            #     parser.get_config(), "data with invalid token is not rejected"
            # )

        except Exception as e:
            output = parser.get_config()
            self._log_error("data sections: {}".format(data.keys()))
            self._log_error("output sections: {}".format(output.keys()))
            self._log_error("data: {}".format(data))
            self._log_error("output: {}".format(output))
            raise e

    def test_write_to_file(self):
        folder = TestFolder()
        folder.save("token.ini", "")
        ini = folder.fullpath("token.ini")
        cfg = make_config_parser()
        parser = ConfigParserMixin(ini, cfg, serialize_keys=("token","name"))
        
        bad_sections = [" "]
        ok_sections = ["A","B"] 
        sections = ok_sections + bad_sections
        data = {s: [
            dict(token="{}{}".format(s,i), name="{}{}".format(s,i)) 
            for i in range(3)
            ]
            for s in sections
        }
        txt = "[A]\nA0,A0\nA1,A1\nA2,A2\n\n[B]\nB0,B0\nB1,B1\nB2,B2\n\n"

        parser.update_config(data)
        folder.save("token.ini", "")
        parser.write_to_file()
        out = folder.load("token.ini")
        try:
            self.assertEqual(
                ok_sections,
                cfg.sections(),
            )
            self._test_ini_valid_sections(out, ok_sections)
            self.assertEqual(txt, out.replace("\r\n","\n"), "ini does not match expected")
        except Exception as e:
            self._log_error("sections:", dict(cfg._sections))
            self._log_error("ini content:\n", txt)
            raise e

    def test_read_from_file(self):
        txt = "[A]\nA0,A0\nA1,A1\nA2,A2\n\n[B]\nB0,B0\nB1,B1\nB2,B2\n\n"
        ok_sections = ["A","B"]

        folder = TestFolder()
        folder.save("token.ini", txt)
        ini = folder.fullpath("token.ini")
        cfg = make_config_parser()
        parser = ConfigParserMixin(ini, cfg, serialize_keys=("token","name"))
        parser.read_from_file()

        try:
            self.assertEqual(
                ok_sections,
                cfg.sections(),
            )

            data = parser.get_config()
            self.assertEqual({
                'A': [
                    {'token': 'A0', 'name': 'A0'}, 
                    {'token': 'A1', 'name': 'A1'}, 
                    {'token': 'A2', 'name': 'A2'}
                    ],
                'B': [
                    {'token':'B0', 'name': 'B0'}, 
                    {'token': 'B1', 'name': 'B1'}, 
                    {'token': 'B2', 'name': 'B2'}
                    ]
                },
                data, "loaded config does not match expected"
            )

            folder.save("token.ini", "")
            parser.write_to_file()
            out = folder.load("token.ini")
            self._test_ini_valid_sections(txt, ok_sections)
            self.assertEqual(txt, out.replace("\r\n","\n"), "ini does not match expected")
        except Exception as e:
            self._log_error("sections:", dict(cfg._sections))
            self._log_error("ini content:\n", txt)
            raise e

    def _test_ini_valid_sections(self, txt, ok_sections):
        matched_sections = re.findall(r"\[(.*)\]", txt)
        self.assertEqual(ok_sections, matched_sections, "unexpected sections found")

        self.assertRegex(
            txt,
            r"\[({})\]".format("|".join(ok_sections)), "unexpected sections found"
        )
        self.assertNotRegex(
            txt,
            r"\[[\s]*\]", "sections with empty name found"
        )

        # invalid name example
        self.assertRegex(
            "[ ]",
            r"\[[\s]*\]", "sections with invalid name found"
        )
        self.assertRegex(
            "[]",
            r"\[[\s]*\]", "sections with invalid name found"
        )
        
if __name__ == "__main__":
    unittest.main()
    # tests = [
    #     "TestConfigParserMixin",
    #     "TestTokenModel",
    # ]
    # unittest.main(defaultTest = tests)
    # unittest.main(defaultTest = tests, failfast=True) # will not run all subtest
