#!/usr/bin/python3

""" ********************************************************

Project: nita-yaml-to-excel

Copyright (c) Juniper Networks, Inc., 2021. All rights reserved.

Notice and Disclaimer: This code is licensed to you under the Apache 2.0 License (the "License"). You may not use this code except in compliance with the License. This code is not an official Juniper product. You can obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0.html

SPDX-License-Identifier: Apache-2.0

Third-Party Code: This code may depend on other components under separate copyright notice and license terms. Your use of the source code for those components is subject to the terms and conditions of the respective license as noted in the Third-Party source code file.

********************************************************"""

import logging
import os
import sys
from collections import OrderedDict

import yaml
from openpyxl import load_workbook

logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
                    format='%(asctime)s: %(levelname)s: %(message)s')

pre_defined_unique_identifiers = ['id', 'name', 'group']


class _OrderedSafeDumper(yaml.SafeDumper):
    """Safe YAML dumper that correctly serialises ``OrderedDict`` and ``None``."""

    def represent_ordered_dict(self, mapping):
        """Represent an ``OrderedDict`` as a regular YAML mapping."""
        return self.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            mapping.items())

    def represent_none(self, _value):
        """Represent ``None`` as an empty YAML string rather than ``null``."""
        return self.represent_scalar('tag:yaml.org,2002:null', '')


_OrderedSafeDumper.add_representer(OrderedDict, _OrderedSafeDumper.represent_ordered_dict)
_OrderedSafeDumper.add_representer(type(None), _OrderedSafeDumper.represent_none)


def ordered_dump(data, stream=None, **kwds):
    """Dump *data* to YAML while preserving ``OrderedDict`` key order.

    Uses a safe dumper, so arbitrary Python objects cannot be serialised.
    ``None`` values are written as empty strings rather than ``null``.

    Args:
        data: Python object to serialise.
        stream: File-like object to write to, or ``None`` to return a string.
        **kwds: Extra keyword arguments forwarded to :func:`yaml.dump`.

    Returns:
        str | None: YAML string when *stream* is ``None``, else ``None``.
    """
    return yaml.dump(data, stream, _OrderedSafeDumper, **kwds)


def stripper(data):
    """Recursively remove empty ``OrderedDict`` values from *data*.

    Drops keys whose value is an empty ``OrderedDict`` or the bare ``list``
    type object; nested dicts are stripped recursively.

    Args:
        data (OrderedDict): The mapping to clean.

    Returns:
        OrderedDict: A new mapping with empty-dict entries removed.
    """
    new_data = OrderedDict()
    for k, v in data.items():
        if isinstance(v, OrderedDict):
            v = stripper(v)
        if v not in (list, OrderedDict()):
            new_data[k] = v
    return new_data


class ExcelToYaml:
    """Convert an Excel workbook produced by ``YamlToExcel`` back to YAML files.

    Sheet layout conventions assumed:

    * **base** — three columns (``host``, ``name``, ``value``) for scalars.
    * **Named sheets** — columns are dot-path keys; rows are per-host data.
    * **Sheets ending with ``+``** — treated as YAML list values.
    """

    # -----------------------------------------------------------------------
    # CONSTRUCTOR
    # -----------------------------------------------------------------------

    def __init__(self, workbook_name_param, dest_dir_param):
        """Initialise the converter.

        Args:
            workbook_name_param (str): Path to the ``.xlsx`` workbook to read.
            dest_dir_param (str): Directory where output YAML files are written.

        Raises:
            Exception: If either argument is an empty string.
        """
        if workbook_name_param == "":
            logging.error("Workbook name required.")
            raise ValueError("Workbook name required.")
        if dest_dir_param == "":
            logging.error("Destination directory required.")
            raise ValueError("Destination directory required.")

        self.workbook_name = workbook_name_param
        self.dest_dir = dest_dir_param
        self.sheet_data = OrderedDict()

    def write_base_sheet_data(self, base_sheet_data, dest_dir):
        """Serialise accumulated sheet data to per-host YAML files.

        Strips empty dicts with :func:`stripper`, serialises each host's data
        with :func:`ordered_dump`, creates intermediate directories as needed,
        and writes the YAML file to ``<dest_dir>/<hostname>``.

        Args:
            base_sheet_data (OrderedDict): Mapping of hostname → nested data.
            dest_dir (str): Root output directory.
        """
        logging.debug("Base sheet data ::: %s ", base_sheet_data)
        for host_file in base_sheet_data:

            base_sheet_data[host_file] = stripper(
                base_sheet_data[host_file])

            base_yaml_content = ordered_dump(
                OrderedDict(base_sheet_data[host_file]),
                default_flow_style=False,
                explicit_start=True)
            logging.debug("Final data-")
            logging.debug(base_yaml_content)

            if not os.path.isdir(dest_dir):
                os.makedirs(dest_dir)

            if host_file:
                host_file_dir = dest_dir + '/' + os.path.dirname(host_file)
                if not os.path.isdir(host_file_dir):
                    os.makedirs(host_file_dir)
                with open(dest_dir + '/' + host_file, 'w', encoding='utf-8') as outfile:
                    outfile.write(base_yaml_content)

    def map_key_value(self, key, value, param_dict):
        """Map a dot-separated *key* and *value* into a nested ``OrderedDict``.

        Recursively inserts *value* at the appropriate nesting level within
        *param_dict* by splitting *key* on ``"."``.
        Blank cells do not create or modify the surrounding hierarchy.

        Args:
            key (str): Dot-separated column header from the spreadsheet.
            value: Parsed cell value.
            param_dict (OrderedDict): Target mapping to update.

        Returns:
            OrderedDict: Updated (or new) mapping containing the key/value.
        """
        value = self.parse_cell_value(value)
        if value == "":
            return param_dict
        splitted_keys = key.split('.')
        mapped_dict = param_dict
        if len(splitted_keys) > 1:

            index = key.find(".")
            first_str = key[: index]
            sliced_str = key[index + 1:]

            if first_str in mapped_dict.keys():
                temp_recursive_dict = mapped_dict[first_str]
                temp_dict = self.map_key_value(
                    sliced_str, value, temp_recursive_dict)
                temp_recursive_dict.update(OrderedDict(temp_dict))
            else:
                temp_dict = self.map_key_value(
                    sliced_str, value, OrderedDict())
                mapped_dict.update(OrderedDict({first_str: temp_dict}))
        else:
            mapped_dict = OrderedDict({key: value})

        return mapped_dict

    def process_data(self, key, value, hostname, sheet_name):
        """Store a key/value pair into the in-memory :attr:`sheet_data`.

        Merges the pair into ``sheet_data[hostname][sheet_name]`` via
        :meth:`map_key_value`, creating new host or sheet entries as needed.

        Args:
            key (str): Dot-separated column key from the spreadsheet.
            value: Parsed cell value.
            hostname (str): The ``host`` column value for this row.
            sheet_name (str): Name of the worksheet being processed.
        """
        logging.debug("Key :: %s Value :: %s ", key, value)

        if hostname in self.sheet_data.keys():
            temp_host_data = self.sheet_data[hostname]
            if sheet_name in temp_host_data.keys():
                temp_sheet_data = temp_host_data[sheet_name]
                temp_dict = self.map_key_value(key, value, temp_sheet_data)
                temp_sheet_data.update(temp_dict)
            else:
                logging.debug("New sheet data ::: ")
                temp_dict = self.map_key_value(key, value, OrderedDict())
                temp_sheet_data = OrderedDict()
                temp_sheet_data.update({sheet_name: temp_dict})
                temp_host_data.update(temp_sheet_data)

        else:
            logging.debug("New hostname found..")
            if hostname != "":
                temp_dict = self.map_key_value(key, value, OrderedDict())
                temp_sheet_data = OrderedDict()
                temp_sheet_data.update({sheet_name: temp_dict})
                host_dict = OrderedDict()
                host_dict.update({hostname: temp_sheet_data})
                self.sheet_data.update(host_dict)

    def get_appropriate_array_data(self, unique_field, unique_value, old_data):
        """Find an existing list entry matching a unique field/value pair.

        Searches *old_data* (a list of ``OrderedDict`` entries) for the first
        entry whose *unique_field* key equals *unique_value*.

        Args:
            unique_field (str): Key name to match (e.g. ``"name"``).
            unique_value: Value to match against.
            old_data (list | OrderedDict): Previously accumulated data.

        Returns:
            OrderedDict: The matching entry, or an empty ``OrderedDict``.
        """
        if old_data:
            if unique_field is not None and unique_value is not None:
                logging.debug("Got it.... %s ", type(old_data))
                if isinstance(old_data, list):
                    for old_dict_data in old_data:
                        if isinstance(old_dict_data, OrderedDict):
                            if unique_field in old_dict_data.keys():
                                if old_dict_data[unique_field] == unique_value:
                                    return old_dict_data

        return OrderedDict()

    def build_recursive_data(self, parentKey, dict_data, old_data):
        """Reconstruct a nested YAML dict from flat spreadsheet row data.

        Processes *dict_data* (with ``+``/``@``-encoded keys) and merges it
        into *old_data*, handling unique identifiers and nested list markers.

        Args:
            parentKey (str | None): Key used to match rows when merging into
                an existing list.
            dict_data (OrderedDict): Flat row data from the spreadsheet.
            old_data (OrderedDict | list): Previously accumulated data.

        Returns:
            OrderedDict: ``{"new_data": ..., "existing_data": ...}``.
        """
        logging.debug("\ndict_data ::: %s ", dict_data)
        logging.debug(" >>> old_data :: %s ", old_data)

        unique_field = ""
        unique_identifier = ""
        first_level_dict_data = OrderedDict()
        hierarchy_dict_data = OrderedDict()

        existing_data = OrderedDict()

        for dict_key in dict_data:
            if old_data:
                if dict_key.find("@") >= 0:
                    logging.debug("Unique identifier ::: ")
                    unique_identifier = dict_key

                if dict_key.find("@") >= 0:
                    index = dict_key.find("@")
                    unique_field = dict_key[index + 1:]

                    logging.debug(
                        "Going to get old dict data .................. %s ", unique_field)
                    existing_data = self.get_appropriate_array_data(
                        unique_field, dict_data[unique_identifier], old_data)
                    if existing_data:
                        first_level_dict_data = existing_data

        for dict_key in dict_data:
            if dict_key.find("@") >= 0:
                unique_identifier = dict_key

            value = dict_data[dict_key]

            if old_data:
                if dict_key.find("@") >= 0:
                    index = dict_key.find("@")
                    unique_field = dict_key[index + 1:]

                    logging.debug(
                        "Going to get old dict data ..................")
                    existing_data = self.get_appropriate_array_data(
                        unique_field, dict_data[unique_identifier], old_data)
                    if existing_data:
                        first_level_dict_data = existing_data

            if dict_key.find("+") >= 0:
                temp_dic_data = None
                index = dict_key.find("+")
                temp_key = dict_key[: index]

                array_data = OrderedDict()
                previous_data = OrderedDict()
                temp_array_hierarchy_data = OrderedDict()
                if isinstance(value, (OrderedDict, list)):
                    if old_data:
                        if isinstance(old_data, OrderedDict):
                            if temp_key in old_data.keys():
                                temp_array_hierarchy_data = old_data[temp_key]
                                first_level_dict_data.update(
                                    OrderedDict({temp_key: old_data[temp_key]}))

                        elif isinstance(old_data, list):
                            for old_data_row in old_data:
                                if temp_key in old_data_row.keys():
                                    if (parentKey is None and (unique_field in first_level_dict_data.keys() and unique_field in old_data_row.keys()
                                                               and old_data_row[unique_field] == first_level_dict_data[unique_field])):
                                        temp_array_hierarchy_data = old_data_row[temp_key]
                                        parentKey = None
                                        break
                                    if (parentKey in old_data_row.keys() and parentKey in first_level_dict_data.keys() and
                                            old_data_row[parentKey] == first_level_dict_data[parentKey]):
                                        temp_array_hierarchy_data = old_data_row[temp_key]
                                        parentKey = None
                                        break

                    temp_dic_data = self.build_recursive_data(
                        parentKey, value, temp_array_hierarchy_data)

                    if temp_dic_data:
                        if "new_data" in temp_dic_data.keys():
                            array_data = temp_dic_data["new_data"]
                        if "existing_data" in temp_dic_data.keys():
                            previous_data = temp_dic_data["existing_data"]
                else:
                    if old_data:
                        if isinstance(old_data, OrderedDict):
                            if temp_key in old_data.keys():
                                first_level_dict_data.update(
                                    OrderedDict({temp_key: old_data[temp_key]}))

                    array_data = value

                if isinstance(array_data, int) or array_data:
                    logging.debug("Not empty.....")
                    if temp_key in first_level_dict_data:
                        temp_array_data = first_level_dict_data[temp_key]
                        if not previous_data:
                            temp_array_data.append(array_data)
                    else:
                        logging.debug("Key not found")
                        first_level_dict_data.update(
                            OrderedDict({temp_key: [array_data]}))

            else:
                if not isinstance(value, (OrderedDict, list)):

                    logging.debug("Not a dict and list %s %s %s",
                                  dict_key, value, type(value))

                    unique_field = dict_key
                    if dict_key.find("@") >= 0:
                        index = dict_key.find("@")
                        unique_field = dict_key[index + 1:]

                    if dict_data[dict_key] != "":
                        first_level_dict_data.update(OrderedDict(
                            {unique_field: dict_data[dict_key]}))
                else:
                    logging.debug("Process hierarchy data %s ", dict_key)
                    if dict_data[dict_key]:
                        hierarchy_dict_data.update(
                            OrderedDict({dict_key: dict_data[dict_key]}))

        if hierarchy_dict_data:
            for hierarchy_key in hierarchy_dict_data:

                temp_array_hierarchy_data = first_level_dict_data.get(
                    hierarchy_key, OrderedDict())

                if isinstance(old_data, OrderedDict):
                    if hierarchy_key in old_data.keys():
                        temp_array_hierarchy_data = old_data[hierarchy_key]

                temp_dic_data = self.build_recursive_data(
                    parentKey, hierarchy_dict_data[hierarchy_key], temp_array_hierarchy_data)

                temp_hierarchy_data = OrderedDict()
                if temp_dic_data:
                    if "new_data" in temp_dic_data.keys():
                        temp_hierarchy_data = temp_dic_data["new_data"]

                if isinstance(temp_array_hierarchy_data, OrderedDict):
                    retained_hierarchy_data = OrderedDict(temp_array_hierarchy_data)
                    retained_hierarchy_data.update(temp_hierarchy_data)
                    temp_hierarchy_data = retained_hierarchy_data

                if temp_hierarchy_data:
                    first_level_dict_data.update(OrderedDict(
                        {hierarchy_key: temp_hierarchy_data}))

        logging.debug("First level dict: %s ", first_level_dict_data)

        return OrderedDict({"new_data":  first_level_dict_data, "existing_data": existing_data})

    def add_hierarical_data(self, parentKey, dict_data, hostname, sheet_name, is_list=True):
        """Merge *dict_data* into the hierarchical in-memory data store.

        Delegates to :meth:`build_recursive_data` and inserts the result under
        ``sheet_data[hostname][sheet_name]``.  Appends to a list when
        *is_list* is ``True``; updates the sheet dict otherwise.

        Args:
            parentKey (str | None): Row identifier key for list merging.
            dict_data (OrderedDict): Flat row data to reconstruct.
            hostname (str): Host key in :attr:`sheet_data`.
            sheet_name (str): Sheet key in the host sub-dict.
            is_list (bool): When ``True``, wrap the result in a list.
        """
        if hostname in self.sheet_data.keys():
            temp_host_data = self.sheet_data[hostname]
            if sheet_name in temp_host_data.keys():
                temp_sheet_data = temp_host_data[sheet_name]
                structured_data = self.build_recursive_data(
                    parentKey, dict_data, temp_sheet_data)
                logging.debug("============================================")
                logging.debug(structured_data)
                if structured_data:
                    if "existing_data" in structured_data.keys():
                        if not structured_data["existing_data"]:
                            structured_data = structured_data["new_data"]
                            if is_list:
                                temp_sheet_data.append(structured_data)
                            else:
                                temp_sheet_data.update(structured_data)
                    else:
                        structured_data = structured_data["new_data"]
                        if is_list:
                            temp_sheet_data.append(structured_data)
                        else:
                            temp_sheet_data.update(structured_data)
            else:
                logging.debug("Going to build new sheet data...")
                structured_data = self.build_recursive_data(
                    parentKey, dict_data, OrderedDict())

                if structured_data:
                    if "new_data" in structured_data.keys():
                        structured_data = structured_data["new_data"]

                temp_sheet_data = OrderedDict()
                if is_list:
                    temp_dict = [structured_data]
                    temp_sheet_data.update(
                        OrderedDict({sheet_name: temp_dict}))
                else:
                    temp_sheet_data.update(OrderedDict(
                        {sheet_name: structured_data}))
                temp_host_data.update(temp_sheet_data)

        else:
            logging.debug("\nGoing to build new host data...")
            structured_data = self.build_recursive_data(
                parentKey, dict_data, OrderedDict())

            if structured_data:
                if "new_data" in structured_data.keys():
                    structured_data = structured_data["new_data"]

            temp_sheet_data = OrderedDict()
            if is_list:
                temp_dict = [structured_data]
                temp_sheet_data.update(OrderedDict({sheet_name: temp_dict}))
            else:
                temp_sheet_data.update(OrderedDict(
                    {sheet_name: structured_data}))
            host_dict = OrderedDict()
            host_dict.update(OrderedDict({hostname: temp_sheet_data}))
            self.sheet_data.update(host_dict)

    def process_list_data(self, parentKey, dict_data, hostname, sheet_name):
        """Route list-type row data into the appropriate in-memory structure.

        Recursively inspects *dict_data* for ``+``/``@``-encoded keys and
        dispatches to :meth:`add_hierarical_data` with the appropriate
        ``is_list`` flag and stripped sheet name.

        Args:
            parentKey (str | None): Row identifier key for list merging.
            dict_data (OrderedDict): Row data from a list-type sheet.
            hostname (str): Host identifier.
            sheet_name (str): Raw sheet name (may include trailing ``+``).
        """
        logging.debug(dict_data)
        logging.debug("keys::::::::::::::::::::::::: %s ", dict_data.keys())

        def needs_reconstruction(data):
            return any(
                key.find("+") > 0 or key.startswith("@")
                or (isinstance(value, OrderedDict) and needs_reconstruction(value))
                for key, value in data.items()
            )

        is_nested = needs_reconstruction(dict_data)

        if is_nested:
            if sheet_name.find("+") > 0:
                sheet_index = sheet_name.find("+")
                sheet_name = sheet_name[: sheet_index]

                self.add_hierarical_data(
                    parentKey, dict_data, hostname, sheet_name, True)

            else:
                logging.debug("List within in dict...")

                self.add_hierarical_data(
                    parentKey, dict_data, hostname, sheet_name, False)

        if not is_nested:
            logging.debug("New Normal dict data...")

            if sheet_name.find("+") > 0:
                sheet_index = sheet_name.find("+")
                sheet_name = sheet_name[: sheet_index]
                logging.debug(sheet_name)

                if hostname in self.sheet_data.keys():
                    temp_host_data = self.sheet_data[hostname]
                    if sheet_name in temp_host_data.keys():
                        temp_sheet_data = temp_host_data[sheet_name]
                        temp_sheet_data.append(OrderedDict(dict_data))
                    else:
                        temp_sheet_data = OrderedDict()
                        temp_dict = [dict_data]
                        temp_sheet_data.update(
                            OrderedDict({sheet_name: temp_dict}))
                        temp_host_data.update(OrderedDict(temp_sheet_data))
                else:
                    temp_sheet_data = OrderedDict()
                    temp_dict = [dict_data]
                    temp_sheet_data.update(
                        OrderedDict({sheet_name: temp_dict}))
                    host_dict = OrderedDict()
                    host_dict.update(OrderedDict({hostname: temp_sheet_data}))
                    self.sheet_data.update(OrderedDict(host_dict))

            else:

                self.add_hierarical_data(
                    parentKey, dict_data, hostname, sheet_name, False)

    def parse_cell_value(self, value):
        """Coerce a raw Excel cell value to a YAML-appropriate Python type.

        ``"None"`` strings are converted to ``None``; ``float`` whole numbers
        are converted to ``int``.

        Args:
            value: Raw cell value from openpyxl.

        Returns:
            The coerced value.
        """
        if value == "None":
            value = None
        if isinstance(value, float):
            value = int(value)

        return value

    def process_by_sheet(self, wb, sheet_name):
        """Read one worksheet and populate :attr:`sheet_data` with its content.

        Dispatches based on sheet name:

        * **base** — reads ``host``/``name``/``value`` column layout.
        * **Other sheets** — reads dot-path column headers per row.

        Args:
            wb: Loaded openpyxl workbook.
            sheet_name (str): Name of the sheet to process.
        """
        sheet = wb[sheet_name]
        if sheet_name == "base":
            logging.debug(
                "This is a base sheet.. Need to handle in different way..")

            hosts_header = 0
            key_header = 1
            value_header = 2

            logging.debug("Sheet has %d columns", sheet.max_column)
            for col in range(1,sheet.max_column+1):
                columnHeader = sheet.cell(1, col).value
                logging.debug("Col = %d, Header= %s",col,columnHeader)
                if columnHeader == "host":
                    hosts_header = col
                elif columnHeader == "name":
                    key_header = col
                elif columnHeader == "value":
                    value_header = col

            for row in range(1,sheet.max_row+1):

                if row != 1:
                    logging.debug("Row = %d, HostsHead = %d,keyhead = %d, valhead = %d",row,hosts_header,key_header,value_header)
                    hostname = sheet.cell(row, hosts_header).value
                    key = sheet.cell(row, key_header).value
                    value = self.parse_cell_value(
                        sheet.cell(row, value_header).value)
                    logging.debug("hostname = %s, key = %s, value=%s",hostname,key,value)
                    is_list = False
                    if key.find("+") > 0:
                        key_index = key.find("+")
                        key = key[: key_index]
                        is_list = True

                    if hostname in self.sheet_data.keys():
                        # temp_data=OrderedDict()
                        temp_data = self.sheet_data[hostname]
                        if is_list:
                            if key in temp_data.keys():
                                temp_data[key].append(value)
                            else:
                                temp_dict = {key: [value]}
                        else:
                            temp_dict = {key: value}
                        temp_data.update(OrderedDict(temp_dict))
                    else:
                        logging.debug("New sheet data..")
                        if is_list:
                            temp_dict = {key: [value]}
                        else:
                            temp_dict = {key: value}
                        host_dict = OrderedDict(
                            {hostname: OrderedDict(temp_dict)})
                        self.sheet_data.update(OrderedDict(host_dict))



        else:
            logging.debug("Other Sheets :: %s ", sheet_name)
            keys = []
            values = []
            for row in range(1,sheet.max_row+1):
                is_header_row = False
                i = 0
                hostname = ""
                array_data = OrderedDict()
                empty_value_count = 0
                for col in range(1,sheet.max_column+1):
                    cell_value = sheet.cell(row, col).value
                    if cell_value is None:
                        cell_value = ""
                    if cell_value == "host":
                        is_header_row = True
                        keys = []

                    if cell_value == "---":
                        keys = []
                        break

                    if is_header_row:
                        keys.append(cell_value)
                    else:
                        values.append(cell_value)
                        if keys[i] == "host":
                            if cell_value != "":
                                hostname = cell_value
                            else:
                                empty_value_count = empty_value_count + 1
                        else:
                            logging.debug("Row = %i, col = %i, key = %s, cell_value = %s",row,col,keys[i],cell_value)
                            if keys[i] != "" and keys[i].find("+") > 0 or sheet_name.find("+") > 0:
                                temp_array_data = self.map_key_value(
                                    keys[i], cell_value, array_data)
                                array_data.update(temp_array_data)

                                if cell_value == "":
                                    empty_value_count = empty_value_count + 1

                            elif keys[i] != "":
                                self.process_data(
                                    keys[i], cell_value, hostname, sheet_name)
                        i = i + 1

                logging.debug(
                    "\n$$$$$$$$$$$$$$ array_data ::: %s ", array_data)
                if i == empty_value_count:
                    array_data = OrderedDict()

                if array_data:
                    if isinstance(array_data, OrderedDict):
                        parentKey = None
                        for key in pre_defined_unique_identifiers:
                            if "@"+key in array_data.keys():
                                parentKey = key
                                break
                        self.process_list_data(
                            parentKey, array_data, hostname, sheet_name)

        logging.debug(self.sheet_data)

    def convert_data(self):
        """Run the Excel → YAML conversion.

        Loads the workbook at :attr:`workbook_name`, iterates over every sheet
        calling :meth:`process_by_sheet`, and writes accumulated data to YAML
        files in :attr:`dest_dir` after each sheet.
        """
        workbook = load_workbook(self.workbook_name)
        logging.debug(workbook.sheetnames)

        for sheet_name in workbook.sheetnames:

            logging.info("Processing sheet %s ", sheet_name)
            self.process_by_sheet(workbook, sheet_name)

            # Write content to yaml files.
            self.write_base_sheet_data(self.sheet_data, self.dest_dir)

        logging.debug("Spreadsheet converted successfully.")


def main():
    """Entry point for the ``xls2yaml`` console script.

    Expects exactly two command-line arguments: the workbook path and the
    destination directory.  Prints usage and returns early on wrong arg count.
    """
    logging.debug(len(sys.argv))
    if len(sys.argv) != 3:
        logging.error(
            "\n\n Usage:\n\n  > xls2yaml.py <workbook name> <destination directory>\n\n Example:\n\n  > xls2yaml.py vDC.xlsx ./\n")
        #raise Exception("Arguments required: xls2yaml.py <workbook name> <destination directory>")
        return

    xls2yaml_instance = ExcelToYaml(sys.argv[1], sys.argv[2])
    xls2yaml_instance.convert_data()


if __name__ == '__main__':
    main()
