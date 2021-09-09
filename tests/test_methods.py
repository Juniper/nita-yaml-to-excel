""" ********************************************************

Project: nita-yaml-to-excel
Version: 21.7

Copyright (c) Juniper Networks, Inc., 2021. All rights reserved.

Notice and Disclaimer: This code is licensed to you under the Apache 2.0 License (the "License"). You may not use this code except in compliance with the License. This code is not an official Juniper product. You can obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0.html

SPDX-License-Identifier: Apache-2.0

Third-Party Code: This code may depend on other components under separate copyright notice and license terms. Your use of the source code for those components is subject to the terms and conditions of the respective license as noted in the Third-Party source code file.

******************************************************** """

from yamltoexcel import yaml2xls
from yamltoexcel import xls2yaml
import unittest
import yaml
import os
from ddt import ddt, data
from collections import OrderedDict


@ddt
class ParserMethodsTestCase(unittest.TestCase):

    @data(5, False, '12.12.12.12', "Test")
    def testParseCellValue(self, value):
        if type(value) is int:
            temp_value = value
        else:
            temp_value = str(value)
        yaml2excel = yaml2xls.YamlToExcel("yaml_file")
        self.assertEqual(yaml2excel.parse_cell_value(value), temp_value)

    def testBuildListData(self):
        input_data = OrderedDict({"boot_server": "10.1.10.134",
                                  "radius_server": "10.1.10.135",
                                  "servers": [
                                      "10.99.0.134",
                                      "10.0.2.5",
                                      "10.10.72.184"
                                  ]
                                  })
        expected_result_data = {"servers": [
            "10.99.0.134", "10.0.2.5", "10.10.72.184"]}
        yaml2excel = yaml2xls.YamlToExcel("yaml_file")
        self.assertEqual(yaml2excel.build_list_data(
            input_data), expected_result_data)

    def testBuildDictData(self):

        input_data = OrderedDict({"boot_server": "10.1.10.134",
                                  "radius_server": "10.1.10.135",
                                  "servers": [
                                      "10.99.0.134",
                                  ]
                                  })
        expected_result_data = {
            "boot_server": "10.1.10.134", "radius_server": "10.1.10.135"}

        yaml2excel = yaml2xls.YamlToExcel("yaml_file")
        self.assertEqual(yaml2excel.build_dict_data(
            input_data), expected_result_data)

        old_data = OrderedDict({"Old_data": "Test"})
        expected_result_data.update(old_data)
        self.assertEqual(yaml2excel.build_dict_data(
            input_data, old_data), expected_result_data)

        expected_result_data = OrderedDict(
            {"ntp.boot_server": "10.1.10.134", "ntp.radius_server": "10.1.10.135"})
        self.assertEqual(yaml2excel.build_dict_data(
            input_data, {}, "ntp"), expected_result_data)

        input_data = OrderedDict({"name": "SKCpolling",
                                  "clients": [
                                      "192.168.0.0/16",
                                      "10.1.0.53/32",
                                      "10.10.7.2/32"
                                  ]
                                  })
        expected_result_data = {'@name': 'SKCpolling'}
        self.assertEqual(yaml2excel.build_dict_data(
            input_data, {}, "", True), expected_result_data)


def runTests():
    suite = unittest.makeSuite(ParserMethodsTestCase, 'test')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == '__main__':
    runTests()
