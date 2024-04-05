[branch]: https://github.com/Juniper/nita/tree/23.12
[readme]: https://github.com/Juniper/nita/blob/23.12/README.md

# NITA YAML-to-Excel 23.12

Welcome to NITA, an open source platform for automating the building and testing of complex networks.

# Release Notes
This project consists of the tools required for manipulating YAML files and Microsoft excel spreadsheet files.

For details about NITA, please refer to the parent [README][readme].

# Installation

NITA YAML-to-Excel is a standalone application that does not require Kubernetes or the other NITA modules. You can simply install it using pip3:

`pip3 install nita-yaml-to-excel/`

# Usage
The most important two programs provided are inside the ``./yamltoexcel`` folder:

```bash
yaml2xls.py <yaml files> <excel spreadsheet name>
```
- This converts a group of yaml files to an excel spreadsheet

```bash
xls2yaml.py <excel spreadsheet name> <destination directory>
```
- This converts an excel spreadsheet into a collection of yaml files

These tools are especially useful when working with NITA project files, to populate the inventory files in YAML format that are used by Ansible.

# Copyright

Copyright 2024, Juniper Networks, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
