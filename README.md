# yaml-to-excel 22.8

Welcome to NITA 22.8

This project consists of the tools required for manipulating YAML files
and Microsoft excel spreadsheet files.

# Copyright

Copyright 2021, Juniper Networks, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Usage
The most important to programs provided are found inside the *yamltoexcel* folder:

```bash
yaml2xls.py <yaml files> <excel spreadsheet name>
```
- Converts a group of yaml files to an excel spreadsheet

```bash
xls2yaml.py <excel spreadsheet name> <destination directory>
```
- Converts an excel spreadsheet into a collection of yaml files

This tool is especially useful when used together with Ansible playbooks in order to populate the inventory files required which are normally specified in YAML format.

# Installation

Using pip3:

`pip3 install nita-yaml-to-excel/`
