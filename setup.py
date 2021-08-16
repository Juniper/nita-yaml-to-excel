#!/usr/bin/env python3

# ********************************************************
#
# Project: nita-yaml-to-excel
# Version: 21.7
#
# Copyright (c) Juniper Networks, Inc., 2021. All rights reserved.
#
# Notice and Disclaimer: This code is licensed to you under the Apache 2.0 License (the "License"). You may not use this code except in compliance with the License. This code is not an official Juniper product. You can obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0.html
#
# SPDX-License-Identifier: Apache-2.0
#
# Third-Party Code: This code may depend on other components under separate copyright notice and license terms. Your use of the source code for those components is subject to the terms and conditions of the respective license as noted in the Third-Party source code file.
#
# ********************************************************

try:
    from setuptools import setup,Command
except ImportError:
    from distutils.core import setup,Command

config = {
    'description': 'Bidirectional conversion of YAML files to Microsoft Excel.',
    'author': 'Juniper Networks',
    'url': 'https://github.com/Juniper/nita-yaml-to-excel',
    'download_url': 'https://github.com/Juniper/nita-yaml-to-excel/archive/refs/heads/21.7.zip',
    'author_email': 'aburston@juniper.net',
    'version': '21.7.0',
    'install_requires': ['PyYAML', 'openpyxl'],
    'packages': ['yamltoexcel'],
    'scripts': ['yamltoexcel/xls2yaml.py', 'yamltoexcel/yaml2xls.py'],
    'name': 'yaml-to-excel'
}

import unittest
if unittest :
	class PyTest(Command):
		user_options = []
		def initialize_options(self): pass
		def finalize_options(self): pass
		def run(self):
			suite = unittest.defaultTestLoader.discover('.')
			unittest.TextTestRunner(verbosity=2).run(suite)

	config['cmdclass'] = { 'test': PyTest }

setup(**config)
