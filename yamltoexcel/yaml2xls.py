#!/usr/bin/env python3

""" ********************************************************

Project: nita-yaml-to-excel

Copyright (c) Juniper Networks, Inc., 2021. All rights reserved.

Notice and Disclaimer: This code is licensed to you under the Apache 2.0 License (the "License"). You may not use this code except in compliance with the License. This code is not an official Juniper product. You can obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0.html

SPDX-License-Identifier: Apache-2.0

Third-Party Code: This code may depend on other components under separate copyright notice and license terms. Your use of the source code for those components is subject to the terms and conditions of the respective license as noted in the Third-Party source code file.

******************************************************** """

import logging
import sys
from collections import OrderedDict

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, NamedStyle, PatternFill, Side
from openpyxl.utils import get_column_letter

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s')

PRE_DEFINED_UNIQUE_IDENTIFIERS = ['id', 'name', 'group']


class _OrderedSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that preserves mapping key order as ``OrderedDict``.

    Booleans are returned as plain strings (``"true"`` / ``"false"``) rather
    than Python ``bool`` values so that round-tripping through Excel is lossless.
    """

    def construct_ordered_mapping(self, node):
        """Construct a YAML mapping node as an ``OrderedDict``."""
        self.flatten_mapping(node)
        return OrderedDict(self.construct_pairs(node))

    def construct_yaml_bool(self, node):
        """Construct YAML bool nodes as plain strings instead of Python bools."""
        return self.construct_scalar(node)


_OrderedSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _OrderedSafeLoader.construct_ordered_mapping)
_OrderedSafeLoader.add_constructor(
    'tag:yaml.org,2002:bool',
    _OrderedSafeLoader.construct_yaml_bool)


def ordered_load(stream):
    """Load YAML from *stream* while preserving mapping key order.

    Booleans are returned as plain strings so that round-tripping through
    Excel is lossless.

    Args:
        stream: File-like object or string containing YAML content.

    Returns:
        OrderedDict: Parsed YAML with preserved key ordering.
    """
    return yaml.load(stream, _OrderedSafeLoader)


class YamlToExcel:
    """Convert one or more YAML files into a single Excel workbook.

    Top-level YAML dict values become named sheets, list values become sheets
    suffixed with ``+``, and scalars are written to the ``base`` sheet.
    The workbook can be converted back to YAML via
    :class:`~yamltoexcel.xls2yaml.ExcelToYaml`.
    """

    def __init__(self, *sysArgs):
        """Initialise the converter with a sequence of file paths.

        Args:
            *sysArgs: Either a single iterable of file-path strings or multiple
                positional string arguments.  The final entry may optionally be
                the output ``.xlsx`` path; if omitted the workbook is saved as
                ``all.xlsx``.
        """
        self.file_params = sysArgs[0] if sysArgs else []

    def column_auto_fit(self, ws, header_value, cell_value, column_index):
        """Resize a worksheet column to fit its header and cell content.

        Width is clamped between 15 and 60 characters.  An extra 5 chars of
        padding is added when the cell value is entirely uppercase.

        Args:
            ws: Target openpyxl worksheet.
            header_value (str): Text of the column header.
            cell_value: Data value being written to the cell.
            column_index (int): 1-based column index to resize.
        """
        max_column_width = 60
        min_column_width = 15

        column_header_width = len(header_value)
        column_value_width = len(str(cell_value))

        if str(cell_value).isupper():
            column_value_width = column_value_width + 5

        column_width = ws.column_dimensions[get_column_letter(
            column_index)].width

        if column_width is None:
            column_width = 0

        if column_value_width > column_width:
            column_width = column_value_width + 5

        if column_header_width > column_width:
            column_width = column_header_width + 5

        column_width = min(column_width, max_column_width)
        column_width = max(column_width, min_column_width)

        ws.column_dimensions[get_column_letter(
            column_index)].width = column_width

    def add_column_header(self, ws, column_name, value, hostname, row_index):
        """Return the column index for *column_name*, creating the header if absent.

        Scans row 1 for a header matching *column_name* (tolerating a leading
        or trailing ``@``).  Appends a new header column when none is found.

        Args:
            ws: Target openpyxl worksheet.
            column_name (str): Header text to locate or create.
            value: Data value about to be written (used for width fitting).
            hostname (str): Current hostname label.
            row_index (int): Current data-row index.

        Returns:
            dict: ``{"row": row_index, "column": column_id}``.
        """
        logging.debug("####################### %s %s %s ",
                      column_name, value, hostname)

        column_count = ws.max_column
        row_id = 1
        # Need to add column header in row = 1 & column = 1
        existing_column_id = 0
        for column_id in range(1, column_count + 1):
            cell_header_value = ws.cell(row=row_id, column=column_id).value
            logging.debug("$$ cell_header_value :: %s %s ",
                          cell_header_value, column_name)
            if (cell_header_value == column_name
                    or (column_name and cell_header_value
                        and (cell_header_value == column_name[1:]
                             or cell_header_value[1:] == column_name))):
                logging.debug(
                    "###Existing column header found in the sheet....")
                existing_column_id = column_id
                break
        logging.debug("Existing column id %s", existing_column_id)
        if existing_column_id == 0:
            ws.cell(row=row_id, column=1).value = "host"
            existing_column_id = ws.max_column + 1
            ws.cell(row=row_id, column=existing_column_id).value = column_name
            ws.cell(row=row_id, column=1).style = "header"
            ws.cell(row=row_id, column=existing_column_id).style = "header"

        row_column_index = {"row": row_index, "column": existing_column_id}

        return row_column_index

    def add_plain_dict_data(self, ws, repeatData, hostname, rIndex=1, addColumnHeader=True):
        """Write a flat ``OrderedDict`` of key/value pairs as a new worksheet row.

        For each key in *repeatData*, resolves (or creates) the column header
        then writes the hostname and value into the next available row.

        Args:
            ws: Target openpyxl worksheet.
            repeatData (OrderedDict): Flat mapping of column-name → cell-value.
            hostname (str): Value written to the ``host`` column.
            rIndex (int): Current logical row index (returned incremented).
            addColumnHeader (bool): Unused – kept for API compatibility.

        Returns:
            int: Updated row index after writing.
        """
        logging.debug("RepeatData ::::::::::::::::::: %s ", repeatData)
        tempcolx = 2
        tempRIndex = ws.max_row
        if isinstance(repeatData, OrderedDict):
            for repkey in repeatData:

                row_column_index = self.add_column_header(ws, repkey, str(
                    repeatData[repkey]), hostname, tempRIndex)

                column_index = 1
                if row_column_index is not None:
                    column_index = row_column_index['column']
                    row_index = row_column_index['row']
                    if column_index is None:
                        column_index = ws.max_column + 1
                    if row_index:
                        tempRIndex = max(tempRIndex, row_index)

                ws.cell(row=tempRIndex + 1, column=1).value = hostname
                ws.cell(row=tempRIndex + 1, column=column_index).value = self.parse_cell_value(repeatData[repkey])
                ws.cell(row = tempRIndex + 1, column = 1).style = "value"
                ws.cell(row = tempRIndex + 1, column = column_index).style = "value"

                # Adjust column width
                self.column_auto_fit(ws, "host", hostname, 1)
                self.column_auto_fit(ws, repkey, repeatData[repkey], column_index)

                tempcolx = tempcolx + 1
            rIndex = rIndex + 1
        return rIndex

    def build_dict_data(self, data, dictData=None, prefix="", put_unique_identifier=False):
        """Flatten a nested ``OrderedDict`` into a single-level dot-keyed mapping.

        Recursively walks *data*, building dot-separated keys from *prefix*.
        List values are skipped.  When *put_unique_identifier* is ``True`` the
        first key matching ``['id', 'name', 'group']`` is prefixed with ``@``.

        Args:
            data (OrderedDict): Source nested mapping to flatten.
            dictData (OrderedDict | None): Accumulator; created when ``None``.
            prefix (str): Dot-separated key path built up during recursion.
            put_unique_identifier (bool): Mark the unique identifier key.

        Returns:
            OrderedDict: Flattened mapping with dot-separated keys.
        """
        logging.debug("Building dict data ....%s %s %s ",
                      data, dictData, put_unique_identifier)
        if not dictData:
            dictData = OrderedDict()
        tDictData = OrderedDict(dictData)

        is_pk_exist = False
        unique_key = ""
        if put_unique_identifier:
            for pk in PRE_DEFINED_UNIQUE_IDENTIFIERS:
                logging.debug("Unique key %s ", pk)
                if isinstance(data, OrderedDict):
                    if pk in data:
                        logging.debug(
                            "Pre defined unique identifier exist... %s", pk)
                        is_pk_exist = True
                        unique_key = pk
                        break

        if isinstance(data, OrderedDict):
            for key in data:
                logging.debug("Key %s ", key)
                logging.debug("Value %s", data[key])
                if is_pk_exist:
                    if unique_key == key:
                        is_pk_exist = False
                        put_unique_identifier = True
                    else:
                        put_unique_identifier = False

                if isinstance(data[key], OrderedDict):
                    if prefix == "":
                        if put_unique_identifier:
                            temp_prefix = '@' + key
                            put_unique_identifier = False
                        else:
                            temp_prefix = key
                    else:
                        if put_unique_identifier:
                            if prefix.find('+') >= 0:
                                temp_prefix = prefix + '.' + '@' + key
                                put_unique_identifier = False
                            else:
                                temp_prefix = prefix + '.' + key
                                put_unique_identifier = False
                        else:
                            temp_prefix = prefix + '.' + key

                    tempDictData = self.build_dict_data(
                        data[key], tDictData, temp_prefix)
                    tDictData.update(tempDictData)
                elif not isinstance(data[key], list):
                    if prefix == "":
                        if put_unique_identifier:
                            tDictData['@' + key] = data[key]
                            put_unique_identifier = False
                        else:
                            tDictData.update(OrderedDict({key: data[key]}))
                    else:
                        if put_unique_identifier:
                            if prefix.find('+') >= 0:
                                tempPre = prefix + '.' + '@' + key
                                put_unique_identifier = False
                            else:
                                tempPre = prefix + '.' + key
                                put_unique_identifier = False
                        else:
                            tempPre = prefix + '.' + key
                        tDictData.update(OrderedDict({tempPre: data[key]}))

        logging.debug("Final ::: tDictData >>> %s ", tDictData)
        return tDictData

    def build_list_data(self, data, listDataParam=None):
        """Extract keys whose values are lists from *data*.

        Args:
            data (OrderedDict): Source mapping to inspect.
            listDataParam (OrderedDict | None): Accumulator; created when ``None``.

        Returns:
            OrderedDict: Mapping of key → list for every list-valued key in
            *data*, or an empty ``OrderedDict`` if none exist.
        """
        logging.debug("Building list data.... %s %s ", data, listDataParam)
        if not listDataParam:
            listDataParam = OrderedDict()

        if isinstance(data, OrderedDict):
            for key in data:
                if isinstance(data[key], list):
                    logging.debug(
                        "-->>>>>>type(data[key]):::: %s", type(data[key]))
                    listDataParam[key] = data[key]

        return listDataParam

    def parse_recursive_data(self, ws, data, oldDictData=None, hostname="", add_column_header=True, rowIndex=1, colIndex=2, prefix=""):
        """Recursively write nested YAML data to a worksheet.

        Handles dicts-containing-lists, plain lists, and plain dicts.
        Delegates leaf-row writing to :meth:`add_plain_dict_data`.

        Args:
            ws: Target openpyxl worksheet.
            data: YAML node (``OrderedDict``, ``list``, or scalar).
            oldDictData (OrderedDict | None): Accumulated flat data from parent
                levels merged into each row.
            hostname (str): Value for the ``host`` column.
            add_column_header (bool): Whether to create column headers.
            rowIndex (int): Current row counter.
            colIndex (int): Starting column index (unused, kept for compat).
            prefix (str): Dot-separated key path from enclosing list context.

        Returns:
            int: Updated row index after writing all rows.
        """
        if not oldDictData:
            oldDictData = OrderedDict()

        tempOldDictData = OrderedDict(oldDictData)
        listData = self.build_list_data(data)
        tempPlainData = self.build_dict_data(
            data, oldDictData, prefix, prefix.endswith('+'))

        logging.debug("listData ::::::: %s ", listData)

        if listData:
            logging.debug("\n\n\nFinal list in dictionary..... parse_recursive_data ...... %s %s %s %s ",
                          listData, rowIndex, tempOldDictData, prefix)
            logging.debug(
                "Dict data with unique identifier ::: parse_recursive_data %s ", tempPlainData)
            for listKey in listData:
                if prefix == "":
                    temp_prefix = listKey
                else:
                    temp_prefix = prefix + '.' + listKey + '+'
                rowIndex = self.parse_recursive_data(
                    ws, listData[listKey], tempPlainData, hostname, add_column_header, rowIndex, colIndex, temp_prefix)
                # rowIndex = rowIndex + 1

        if isinstance(data, list):
            logging.debug("$$$$$$$$$$$$$$$List.... %s ", data)
            addColumnHeader = add_column_header
            for tempData in data:
                if isinstance(tempData, list):
                    logging.debug("To handle list ")
                elif isinstance(tempData, OrderedDict):
                    logging.debug(
                        "####################################### Dict .......... %s %s %s ", tempData, tempOldDictData, prefix)
                    previousRowIndex = rowIndex
                    rowIndex = self.parse_recursive_data(
                        ws, tempData, oldDictData, hostname, add_column_header, rowIndex, colIndex, prefix)
                    if rowIndex == previousRowIndex:
                        tempDictData = self.build_dict_data(
                            tempData, tempOldDictData, prefix)
                        rowIndex = self.add_plain_dict_data(
                            ws, tempDictData, hostname, rowIndex, addColumnHeader)
                else:
                    logging.debug(
                        "Not dict and list :::::::: old data %s %s ", tempData, prefix)
                    tempRepeatData = tempOldDictData
                    tempRepeatData[prefix] = tempData
                    rowIndex = self.add_plain_dict_data(
                        ws, tempRepeatData, hostname, rowIndex, addColumnHeader)

        if isinstance(data, OrderedDict):
            for temp_key in data:
                if isinstance(data[temp_key], OrderedDict):
                    if prefix == "":
                        temp_prefix = temp_key
                    else:
                        temp_prefix = prefix + '.' + temp_key
                    rowIndex = self.parse_recursive_data(
                        ws, data[temp_key], tempPlainData, hostname, add_column_header, rowIndex, colIndex, temp_prefix)
                    logging.debug("rowIndex :: %s ", rowIndex)

        return rowIndex

    def generate_sheet_data(self, ws, data, oldDictData=None, hostname="", add_unique_field=False, add_column_header=True, rowIndex=1, colIndex=2, prefix=""):
        """Write a top-level YAML dict value to a worksheet, handling all nesting.

        Flat mappings are written directly; mappings containing lists are
        decomposed and delegated to :meth:`parse_recursive_data`.

        Args:
            ws: Target openpyxl worksheet.
            data (OrderedDict | list): YAML value to write.
            oldDictData (OrderedDict | None): Carry-over flat data from caller.
            hostname (str): Value for the ``host`` column.
            add_unique_field (bool): Mark the unique identifier key with ``@``.
            add_column_header (bool): Whether to create column headers.
            rowIndex (int): Current row counter.
            colIndex (int): Starting column index (unused, kept for compat).
            prefix (str): Dot-separated key path prefix.

        Returns:
            int: Updated row index after writing.
        """
        if not oldDictData:
            oldDictData = OrderedDict()

        tempOldDictData = OrderedDict(oldDictData)

        listData = self.build_list_data(data)
        tempPlainData = OrderedDict()

        if not listData:
            logging.debug("\n###########################List is empty...")
            tempDictData = self.build_dict_data(data, tempOldDictData, prefix)
            rowIndex = self.add_plain_dict_data(
                ws, tempDictData, hostname, rowIndex, add_column_header)
            logging.debug("testRowIndex :::::::::::: %s", rowIndex)
            for removeKey in tempDictData:
                data.pop(removeKey, None)
        else:
            logging.debug(
                "\n\n\nFinal list in dictionary..... %s %s %s ", listData, rowIndex, prefix)
            tempPlainData = self.build_dict_data(
                data, oldDictData, prefix, add_unique_field)
            logging.debug(
                "Dict data with unique identifier ::: %s", tempPlainData)
            for listKey in listData:
                logging.debug("List key :: %s ", listKey)
                if prefix == "":
                    temp_prefix = listKey + '+'
                else:
                    temp_prefix = prefix + '.' + listKey + '+'
                rowIndex = self.parse_recursive_data(
                    ws, listData[listKey], tempPlainData, hostname, add_column_header, rowIndex, colIndex, temp_prefix)

                if listKey in data:
                    del data[listKey]

            for removeKey in tempPlainData:
                if removeKey in data:
                    del data[removeKey]

        logging.debug("$$$$$$$$$$$$$$$$$$$$$$ data :::: %s", data)

        if data:
            rowIndex = self.parse_recursive_data(
                ws, data, tempPlainData, hostname, add_column_header, rowIndex, colIndex)

        logging.debug("$$$$$$$$$$$$$$$$$$$$$$ rowIndex :::: %s", rowIndex)

        return rowIndex

    def parse_yaml_files(self, wb, ws, file_content, hostname, sheet_last_row_index):
        """Parse a loaded YAML document and distribute its data into *wb*.

        Iterates over top-level keys and dispatches:

        * ``OrderedDict`` values → a named sheet.
        * ``list`` values → a sheet named ``<key>+``.
        * Scalars → the ``base`` sheet (host / name / value columns).

        Args:
            wb: Target openpyxl workbook.
            ws: The ``base`` worksheet.
            file_content (OrderedDict): Parsed YAML content for one host.
            hostname (str): YAML file path used as the host identifier.
            sheet_last_row_index (dict): Mutable mapping of sheet name → last
                written row index, updated in place.
        """
        for key in file_content:
            if isinstance(key, OrderedDict):
                logging.warning("The base list is empty.")
                return
            value = file_content[key]

            if isinstance(value, OrderedDict):
                is_sheet_already_exist = key in wb.sheetnames

                temp_row_index = 1
                add_column_header = True
                if is_sheet_already_exist:
                    additionalws = wb[key]
                    existing_sheet_row_index = sheet_last_row_index[key]
                    temp_row_index = existing_sheet_row_index
                else:
                    additionalws = wb.create_sheet(title=key)
                    additionalws.cell(row=1, column=1).value = "host"

                additional_sheet_row_index = self.generate_sheet_data(
                    additionalws, value, OrderedDict(), hostname, False, add_column_header, temp_row_index)
                sheet_last_row_index[key] = additional_sheet_row_index

            elif isinstance(value, list):

                logging.debug(
                    "\nIt is a list -- Key :: %s Value :: %s ", key, value)
                key = key + "+"
                is_sheet_already_exist = key in wb.sheetnames

                tempRowIndex = 1
                add_column_header = True
                if is_sheet_already_exist:
                    additionalws = wb[key]
                    existing_sheet_row_index = sheet_last_row_index[key]
                    tempRowIndex = existing_sheet_row_index
                else:
                    additionalws = wb.create_sheet(title=key)

                need_remove_sheet = False
                for listTemp in value:
                    logging.debug("\n listTemp ::: %s ", listTemp)
                    if isinstance(listTemp, (list, OrderedDict)):
                        self.generate_sheet_data(
                            additionalws, listTemp, OrderedDict(), hostname, True, False, tempRowIndex)
                        tempRowIndex = tempRowIndex + 1
                    else:
                        logging.debug("Not a list or dict...")
                        base_sheet_rowx = sheet_last_row_index['base']
                        ws.cell(row = base_sheet_rowx + 1, column = 1).value = hostname
                        ws.cell(row = base_sheet_rowx + 1, column = 1).style = "value"
                        ws.cell(row = base_sheet_rowx + 1, column = 2).value = key
                        ws.cell(row = base_sheet_rowx + 1, column = 2).style = "value"
                        ws.cell(row = base_sheet_rowx + 1, column = 3).value = self.parse_cell_value(listTemp)
                        ws.cell(row = base_sheet_rowx + 1, column = 3).style = "value"

                        sheet_last_row_index['base'] = base_sheet_rowx + 1
                        need_remove_sheet = True

                # Clean up sheet
                if need_remove_sheet:
                    cleanupsheet = wb[key]
                    if cleanupsheet is not None:
                        wb.remove(cleanupsheet)

                sheet_last_row_index[key] = tempRowIndex
            else:
                logging.debug("base: %s", key)
                logging.debug("type: %s", type(value))
                logging.debug(self.parse_cell_value(file_content[key]))

                base_sheet_rowx = sheet_last_row_index['base']
                ws.cell(row=base_sheet_rowx + 1, column=1).value = hostname
                ws.cell(row=base_sheet_rowx + 1, column=1).style = "value"
                ws.cell(row=base_sheet_rowx + 1, column=2).value = key
                ws.cell(row=base_sheet_rowx + 1, column=2).style = "value"
                ws.cell(row=base_sheet_rowx + 1, column=3).value = self.parse_cell_value(file_content[key])
                ws.cell(row=base_sheet_rowx + 1, column=3).style = "value"

                # Adjust column width
                self.column_auto_fit(ws, "host", hostname, 1)
                self.column_auto_fit(ws, "Name", key, 2)
                self.column_auto_fit(ws, "Value", file_content[key], 3)

                sheet_last_row_index['base'] = base_sheet_rowx + 1

    def parse_cell_value(self, value):
        """Coerce *value* to an Excel-safe type.

        ``bool`` → ``str``; ``int`` stays ``int``; everything else → ``str``.

        Args:
            value: Raw Python value from the YAML document.

        Returns:
            int | str: A value safe to write into an openpyxl cell.
        """
        if isinstance(value, bool):
            value = str(value)
        elif not isinstance(value, int):
            value = str(value)

        return value

    def put_border(self, wb):
        """Apply a thin black border to every cell in every sheet of *wb*.

        Args:
            wb: openpyxl workbook to decorate.
        """
        thin = Side(border_style="thin", color="000000")
        border = Border(top=thin, left=thin, right=thin, bottom=thin)

        for sheet in wb:
            for rows in sheet.rows:
                for cell in rows:
                    cell.border = border

    def convert_data(self):
        """Run the YAML → Excel conversion and save the workbook.

        Creates a workbook with a ``base`` sheet, registers ``value`` and
        ``header`` named styles, loads each YAML file from :attr:`file_params`,
        and saves to the explicit ``.xlsx`` path when provided, otherwise to
        ``all.xlsx``.
        """
        wb = Workbook()

        ws = wb.active
        ws.title = 'base'

        value_font = Font(name="Bitstream Charter", size=10)
        vthin = Side(border_style="thin", color="000000")
        vborder = Border(top=vthin, left=vthin, right=vthin, bottom=vthin)
        valignment = Alignment(wrap_text=True)

        value_style = NamedStyle(name = "value", font = value_font, border = vborder, alignment = valignment)
        wb.add_named_style(value_style)

        header_font = Font(name="Bitstream Charter", size=10, bold=True)
        hthin = Side(border_style="thin", color="000000")
        hfill = PatternFill(fill_type='solid', fgColor="33bbff")
        hborder = Border(top=hthin, left=hthin, right=hthin, bottom=hthin)

        header_style = NamedStyle(name = "header", font = header_font, fill = hfill, border = hborder)
        wb.add_named_style(header_style)

        ws.cell(row=1, column=1).value = "host"
        ws.cell(row=1, column=1).style = "header"
        ws.cell(row=1, column=2).value = "name"
        ws.cell(row=1, column=2).style = "header"
        ws.cell(row=1, column=3).value = "value"
        ws.cell(row=1, column=3).style = "header"

        sheet_last_row_index = {}

        sheet_last_row_index['base'] = 1

        logging.debug(self.file_params)

        param_len = len(self.file_params)
        if param_len == 1:
            if not self.file_params[0].endswith(".yaml") and not self.file_params[0].endswith(".yml"):
                logging.error(
                    "\n\n Usage:\n\n > yaml2xls.py <yaml-files-path> [spreadsheet-name] Optional \n\n Examples:\n\n > yaml2xls.py group_vars/* host_vars/* vDC.xlsx\n > yaml2xls.py group_vars/* vDC.xlsx\n")
                return

        spreadsheet_file_name = ""
        count = 1
        yaml_file_count = 0
        for file_name in self.file_params:
            if not file_name.endswith("yaml2xls.py"):
                if count == param_len:
                    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
                        spreadsheet_file_name = file_name
                    else:
                        if not file_name.endswith(".yaml") and not file_name.endswith(".yml"):
                            logging.error(
                                "Invalid spreadsheet file extension given.")
                            return
                        yaml_file_count = yaml_file_count + 1
                else:
                    if not file_name.endswith(".yaml") and not file_name.endswith(".yml"):
                        logging.error(
                            "'%s' file is an invalid file. Please give .yaml or .yml file.", file_name)
                        return
                    yaml_file_count = yaml_file_count + 1

            count = count + 1

        if yaml_file_count == 0:
            logging.error(
                'Please give at least one .yaml or .yml file as input.')
            return

        is_empty = True
        for file_name in self.file_params:
            if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                logging.debug("YAML or YML file: %s", file_name)

                with open(file_name, 'r', encoding='utf-8') as stream:
                    content = ordered_load(stream)

                host_name = file_name
                self.parse_yaml_files(
                    wb, ws, content, host_name, sheet_last_row_index)
                is_empty = False

        if not is_empty:
            logging.debug("YAML to excel conversion completed.")
            if spreadsheet_file_name:
                wb.save(spreadsheet_file_name)
            else:
                wb.save("all.xlsx")

def main():
    """Entry point for the ``yaml2xls`` console script."""
    YamlToExcel(sys.argv[1:]).convert_data()


if __name__ == '__main__':
    main()
