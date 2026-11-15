""" ********************************************************

Project: nita-yaml-to-excel

Copyright (c) Juniper Networks, Inc., 2021. All rights reserved.

Notice and Disclaimer: This code is licensed to you under the Apache 2.0 License
(the "License"). You may not use this code except in compliance with the License.
This code is not an official Juniper product. You can obtain a copy of the License
at https://www.apache.org/licenses/LICENSE-2.0.html

SPDX-License-Identifier: Apache-2.0

Third-Party Code: This code may depend on other components under separate copyright
notice and license terms. Your use of the source code for those components is subject
to the terms and conditions of the respective license as noted in the Third-Party
source code file.

******************************************************** """
import os
from collections import OrderedDict

import pytest
import yaml
from openpyxl import Workbook, load_workbook

from yamltoexcel.xls2yaml import ExcelToYaml, ordered_dump, stripper
from yamltoexcel.yaml2xls import YamlToExcel, ordered_load


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_excel_to_yaml(wb_path="dummy.xlsx", dest="."):
    """Return an :class:`ExcelToYaml` instance without raising."""
    return ExcelToYaml(wb_path, dest)


def _simple_workbook(tmp_path, content: dict) -> str:
    """Write *content* as a YAML file, convert to xlsx, return xlsx path."""
    yaml_path = str(tmp_path / "host.yaml")
    xlsx_path = str(tmp_path / "out.xlsx")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f, default_flow_style=False, explicit_start=True)
    return xlsx_path


# ===========================================================================
# yaml2xls – module-level helpers
# ===========================================================================

class TestAddBool:
    """Tests for the :func:`add_bool` YAML constructor override."""

    def test_bool_loaded_as_string_true(self):
        """``true`` in YAML is loaded as the string ``"true"`` (raw scalar)."""
        result = ordered_load("flag: true")
        assert result["flag"] == "true"

    def test_bool_loaded_as_string_false(self):
        """``false`` in YAML is loaded as the string ``"false"`` (raw scalar)."""
        result = ordered_load("flag: false")
        assert result["flag"] == "false"


class TestOrderedLoad:
    """Tests for :func:`ordered_load`."""

    def test_preserves_insertion_order(self):
        """Keys returned in YAML document order."""
        data = ordered_load("z: 1\na: 2\nm: 3")
        assert list(data.keys()) == ["z", "a", "m"]

    def test_returns_ordered_dict(self):
        """Return type is ``OrderedDict``."""
        data = ordered_load("key: value")
        assert isinstance(data, OrderedDict)


# ===========================================================================
# yaml2xls – YamlToExcel methods
# ===========================================================================

class TestYamlToExcelParseCellValue:
    """Tests for :meth:`YamlToExcel.parse_cell_value`."""

    y: YamlToExcel

    def setup_method(self):
        """Initialise converter instance for each test."""
        self.y = YamlToExcel([])

    def test_bool_true_becomes_string(self):
        """True is coerced to the string 'True'."""
        assert self.y.parse_cell_value(True) == "True"

    def test_bool_false_becomes_string(self):
        """False is coerced to the string 'False'."""
        assert self.y.parse_cell_value(False) == "False"

    def test_int_unchanged(self):
        """Integer values pass through unchanged."""
        assert self.y.parse_cell_value(42) == 42

    def test_float_becomes_string(self):
        """Float values are converted to strings."""
        assert self.y.parse_cell_value(3.14) == "3.14"

    def test_none_becomes_string(self):
        """None is converted to the string 'None'."""
        assert self.y.parse_cell_value(None) == "None"


class TestColumnAutoFit:
    """Tests for :meth:`YamlToExcel.column_auto_fit`."""

    y: YamlToExcel
    wb: Workbook
    ws: object

    def setup_method(self):
        """Initialise workbook and worksheet for each test."""
        self.y = YamlToExcel([])
        self.wb = Workbook()
        self.ws = self.wb.active

    def test_uppercase_adds_padding(self):
        """All-uppercase cell value widens the column by 5."""
        self.y.column_auto_fit(self.ws, "header", "ALLCAPS", 1)
        width = self.ws.column_dimensions["A"].width
        assert width >= 15  # at minimum min_column_width

    def test_long_header_clamps_to_max(self):
        """A very long header is clamped to max_column_width (60)."""
        long_header = "x" * 200
        self.y.column_auto_fit(self.ws, long_header, "v", 1)
        width = self.ws.column_dimensions["A"].width
        assert width == 60

    def test_short_value_uses_min_width(self):
        """A one-character value still results in min_column_width (15)."""
        self.y.column_auto_fit(self.ws, "h", "v", 1)
        width = self.ws.column_dimensions["A"].width
        assert width == 15


class TestPutBorder:
    """Tests for :meth:`YamlToExcel.put_border`."""

    def test_border_applied_to_all_cells(self):
        """Every cell in every sheet receives a thin border after put_border."""
        y = YamlToExcel([])
        wb = Workbook()
        ws = wb.active
        ws["A1"] = "hello"
        ws["B2"] = "world"
        y.put_border(wb)
        for sheet in wb:
            for row in sheet.rows:
                for cell in row:
                    assert cell.border.top.border_style == "thin"
                    assert cell.border.left.border_style == "thin"


class TestConvertDataValidation:
    """Tests for the validation logic in :meth:`YamlToExcel.convert_data`."""

    def test_single_non_yaml_file_returns_early(self, tmp_path):
        """A single file with no yaml/yml extension logs an error and returns."""
        y = YamlToExcel([str(tmp_path / "data.txt")])
        # Should not raise; just return early
        y.convert_data()

    def test_invalid_extension_in_middle_returns_early(self, tmp_path):
        """A non-yaml file before the last entry aborts conversion."""
        bad = str(tmp_path / "bad.txt")
        out = str(tmp_path / "out.xlsx")
        with open(bad, "w", encoding="utf-8"):
            pass
        y = YamlToExcel([bad, out])
        y.convert_data()  # must not raise

    def test_no_yaml_files_given_returns_early(self, tmp_path):
        """Only an xlsx path (no yaml) logs error and returns without saving."""
        out = str(tmp_path / "out.xlsx")
        y = YamlToExcel([out])
        y.convert_data()
        assert not os.path.exists(out)

    def test_valid_yaml_saves_xlsx(self, tmp_path):
        """A valid yaml file produces an xlsx workbook."""
        yaml_path = str(tmp_path / "data.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("key: value\n")
        y = YamlToExcel([yaml_path, str(tmp_path / "out.xlsx")])
        y.convert_data()
        assert os.path.exists(str(tmp_path / "out.xlsx"))

    def test_invalid_last_extension_returns_early(self, tmp_path):
        """Two files where the last is neither yaml/yml/xlsx aborts."""
        yaml_path = str(tmp_path / "a.yaml")
        bad = str(tmp_path / "b.csv")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("key: value\n")
        with open(bad, "w", encoding="utf-8"):
            pass
        y = YamlToExcel([yaml_path, bad])
        y.convert_data()  # must not raise


class TestBuildDictDataPrefixWithPlus:
    """Tests for :meth:`YamlToExcel.build_dict_data` with ``+`` in prefix."""

    def setup_method(self):
        self.y = YamlToExcel([])

    def test_prefix_with_plus_and_unique_identifier(self):
        """When prefix contains '+', unique identifier key is prefixed with '@'."""
        data = OrderedDict({"name": "router1", "ip": "10.0.0.1"})
        result = self.y.build_dict_data(data, {}, "devices+", True)
        # The '@name' key should appear because prefix contains '+' and name is
        # a pre-defined unique identifier
        assert "@name" in result or "devices+.@name" in result or "devices+.name" in result

    def test_prefix_without_plus_with_unique_identifier(self):
        """When prefix has no '+', prefix is appended but no '@' added."""
        data = OrderedDict({"name": "router1", "ip": "10.0.0.1"})
        result = self.y.build_dict_data(data, {}, "devices", True)
        assert "devices.@name" in result or "devices.name" in result


# ===========================================================================
# xls2yaml – module-level helpers
# ===========================================================================

class TestOrderedDump:
    """Tests for :func:`ordered_dump`."""

    def test_preserves_order(self):
        """Keys appear in insertion order in the YAML output."""
        data = OrderedDict([("z", 1), ("a", 2), ("m", 3)])
        result = ordered_dump(data, default_flow_style=False)
        lines = [l.split(":")[0] for l in result.strip().splitlines()]
        assert lines == ["z", "a", "m"]

    def test_none_becomes_empty_string(self):
        """``None`` values are emitted as empty YAML strings."""
        data = OrderedDict([("key", None)])
        result = ordered_dump(data)
        assert "key:" in result

    def test_returns_string_when_no_stream(self):
        """Returns a ``str`` when no stream is provided."""
        result = ordered_dump(OrderedDict([("k", "v")]))
        assert isinstance(result, str)


class TestStripper:
    """Tests for :func:`stripper`."""

    def test_removes_empty_ordered_dicts(self):
        """Empty nested ``OrderedDict`` values are dropped."""
        data = OrderedDict([
            ("keep", "value"),
            ("drop", OrderedDict()),
        ])
        result = stripper(data)
        assert "keep" in result
        assert "drop" not in result

    def test_recurses_into_nested_dicts(self):
        """Strips empty dicts inside nested ``OrderedDict`` values."""
        inner = OrderedDict([("a", "1"), ("empty", OrderedDict())])
        data = OrderedDict([("outer", inner)])
        result = stripper(data)
        assert "a" in result["outer"]
        assert "empty" not in result["outer"]

    def test_preserves_non_empty_values(self):
        """Non-empty dict values are retained."""
        data = OrderedDict([("x", OrderedDict([("y", "z")]))])
        result = stripper(data)
        assert result["x"]["y"] == "z"


# ===========================================================================
# xls2yaml – ExcelToYaml
# ===========================================================================

class TestExcelToYamlInit:
    """Tests for :meth:`ExcelToYaml.__init__`."""

    def test_empty_workbook_name_raises(self):
        """Empty workbook_name raises an Exception."""
        with pytest.raises(Exception, match="Workbook name required"):
            ExcelToYaml("", "/tmp")

    def test_empty_dest_dir_raises(self):
        """Empty dest_dir raises an Exception."""
        with pytest.raises(Exception, match="Destination directory required"):
            ExcelToYaml("file.xlsx", "")

    def test_valid_args_sets_attributes(self):
        """Valid arguments initialise attributes correctly."""
        obj = ExcelToYaml("book.xlsx", "/out")
        assert obj.workbook_name == "book.xlsx"
        assert obj.dest_dir == "/out"
        assert isinstance(obj.sheet_data, OrderedDict)


class TestExcelToYamlParseCellValue:
    """Tests for :meth:`ExcelToYaml.parse_cell_value`."""

    def setup_method(self):
        self.e = ExcelToYaml("dummy.xlsx", "/tmp")

    def test_none_string_becomes_none(self):
        assert self.e.parse_cell_value("None") is None

    def test_float_becomes_int(self):
        assert self.e.parse_cell_value(2.0) == 2
        assert isinstance(self.e.parse_cell_value(2.0), int)

    def test_int_unchanged(self):
        assert self.e.parse_cell_value(5) == 5

    def test_string_unchanged(self):
        assert self.e.parse_cell_value("hello") == "hello"

    def test_none_value_unchanged(self):
        """Python ``None`` (not the string) passes through."""
        assert self.e.parse_cell_value(None) is None


class TestMapKeyValue:
    """Tests for :meth:`ExcelToYaml.map_key_value`."""

    def setup_method(self):
        self.e = ExcelToYaml("dummy.xlsx", "/tmp")

    def test_single_key(self):
        """A non-dotted key creates a flat mapping."""
        result = self.e.map_key_value("key", "val", OrderedDict())
        assert result == OrderedDict({"key": "val"})

    def test_empty_value_returns_empty_dict(self):
        """An empty value returns an empty ``OrderedDict``."""
        result = self.e.map_key_value("key", "", OrderedDict())
        assert result == OrderedDict()

    def test_dotted_key_creates_nested_dict(self):
        """A dotted key like ``a.b`` creates a nested structure."""
        result = self.e.map_key_value("a.b", "v", OrderedDict())
        assert result["a"]["b"] == "v"

    def test_dotted_key_existing_parent_merges(self):
        """When the top-level key already exists its dict is updated in place."""
        existing = OrderedDict({"a": OrderedDict({"x": "1"})})
        result = self.e.map_key_value("a.b", "2", existing)
        assert result["a"]["x"] == "1"
        assert result["a"]["b"] == "2"

    def test_deeply_nested_key(self):
        """Three-level dot-separated key produces three levels of nesting."""
        result = self.e.map_key_value("a.b.c", "deep", OrderedDict())
        assert result["a"]["b"]["c"] == "deep"


class TestProcessData:
    """Tests for :meth:`ExcelToYaml.process_data`."""

    def setup_method(self):
        self.e = ExcelToYaml("dummy.xlsx", "/tmp")

    def test_new_host_and_sheet(self):
        """A new hostname and sheet_name are created on first call."""
        self.e.process_data("key", "val", "host1", "sheet1")
        assert "host1" in self.e.sheet_data
        assert "sheet1" in self.e.sheet_data["host1"]

    def test_existing_host_new_sheet(self):
        """An existing hostname with a new sheet_name adds the sheet."""
        self.e.process_data("key", "val", "host1", "sheet1")
        self.e.process_data("key2", "val2", "host1", "sheet2")
        assert "sheet2" in self.e.sheet_data["host1"]

    def test_existing_host_existing_sheet_merges(self):
        """Repeated calls for the same host/sheet accumulate key-value pairs."""
        self.e.process_data("k1", "v1", "host1", "sheet1")
        self.e.process_data("k2", "v2", "host1", "sheet1")
        sheet = self.e.sheet_data["host1"]["sheet1"]
        assert sheet["k1"] == "v1"
        assert sheet["k2"] == "v2"

    def test_empty_hostname_ignored(self):
        """An empty hostname does not add an entry to sheet_data."""
        self.e.process_data("k", "v", "", "sheet1")
        assert "" not in self.e.sheet_data


class TestGetAppropriateArrayData:
    """Tests for :meth:`ExcelToYaml.get_appropriate_array_data`."""

    def setup_method(self):
        self.e = ExcelToYaml("dummy.xlsx", "/tmp")

    def test_match_returns_dict(self):
        """Returns the matching ``OrderedDict`` when found."""
        old = [
            OrderedDict({"name": "r1", "ip": "1.1.1.1"}),
            OrderedDict({"name": "r2", "ip": "2.2.2.2"}),
        ]
        result = self.e.get_appropriate_array_data("name", "r2", old)
        assert result["ip"] == "2.2.2.2"

    def test_no_match_returns_empty(self):
        """Returns an empty ``OrderedDict`` when no match is found."""
        old = [OrderedDict({"name": "r1"})]
        result = self.e.get_appropriate_array_data("name", "missing", old)
        assert result == OrderedDict()

    def test_empty_old_data_returns_empty(self):
        """Returns an empty ``OrderedDict`` when *old_data* is empty."""
        result = self.e.get_appropriate_array_data("name", "r1", [])
        assert result == OrderedDict()

    def test_none_unique_field_returns_empty(self):
        """Returns empty dict when *unique_field* is ``None``."""
        result = self.e.get_appropriate_array_data(None, "v", [OrderedDict()])
        assert result == OrderedDict()


class TestRoundTrip:
    """End-to-end round-trip tests exercising both converters."""

    def _round_trip(self, tmp_path, yaml_content: str) -> dict:
        """Write yaml, convert to xlsx, convert back, return final dict."""
        yaml_path = str(tmp_path / "input.yaml")
        xlsx_path = str(tmp_path / "out.xlsx")
        initial = yaml.safe_load(yaml_content)
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(initial, f, default_flow_style=False, explicit_start=True)
        YamlToExcel([yaml_path, xlsx_path]).convert_data()
        converter = ExcelToYaml(xlsx_path, str(tmp_path))
        converter.convert_data()
        return converter.sheet_data[yaml_path]

    def test_scalar_round_trip(self, tmp_path):
        """Plain scalar values survive the round-trip."""
        result = self._round_trip(tmp_path, "port: 22\nuser: admin\n")
        assert result["port"] == 22
        assert result["user"] == "admin"

    def test_nested_dict_round_trip(self, tmp_path):
        """Nested dicts survive the round-trip."""
        content = "ntp:\n  server: 10.0.0.1\n  port: 123\n"
        result = self._round_trip(tmp_path, content)
        assert result["ntp"]["server"] == "10.0.0.1"

    def test_simple_list_round_trip(self, tmp_path):
        """A top-level key with a list of scalars survives the round-trip."""
        content = "dns:\n  - 8.8.8.8\n  - 8.8.4.4\n"
        result = self._round_trip(tmp_path, content)
        assert "8.8.8.8" in result["dns"]

    def test_nested_protocol_rows_preserve_parent_instance_names(self, tmp_path):
        content = """
routing_instances:
  instance:
    - name: VRF_10001
      interface:
        - name: irb.1001
      protocols:
        ospf:
          area:
            - name: 0.0.0.0
              interface:
                - name: xe-0/0/2.1
                  metric: 100
                - name: xe-0/0/3.1
                  metric: 200
    - name: VRF_10002
      interface:
        - name: irb.2001
      protocols:
        ospf:
          area:
            - name: 0.0.0.0
              interface:
                - name: xe-0/0/2.2
                  metric: 300
"""
        assert self._round_trip(tmp_path, content) == yaml.safe_load(content)

    def test_nested_protocols_survive_with_parent_key_after_nested_data(self, tmp_path):
        content = """
routing_instances:
  instance:
    - interface:
        - name: irb.1001
      protocols:
        ospf:
          reference_bandwidth: 100
          area:
            - interface:
                - metric: 100
                  name: xe-0/0/2.1
                - metric: 200
                  name: xe-0/0/3.1
              name: 0.0.0.0
      name: VRF_10001
    - protocols:
        ospf:
          area:
            - interface:
                - name: xe-0/0/2.2
              name: 0.0.0.0
      name: VRF_10002
"""
        expected = {}
        for hostname, host_content in (
            ("host1.yaml", content),
            ("host2.yaml", content.replace("VRF_1000", "VRF_2000")),
        ):
            yaml_path = tmp_path / hostname
            yaml_path.write_text(host_content)
            expected[str(yaml_path)] = yaml.safe_load(host_content)
        xlsx_path = tmp_path / "out.xlsx"
        YamlToExcel([*expected, str(xlsx_path)]).convert_data()
        converter = ExcelToYaml(str(xlsx_path), str(tmp_path))
        workbook = load_workbook(xlsx_path)
        sheet = workbook["routing_instances"]
        headers = next(sheet.values)
        protocol_rows = 0
        for values in list(sheet.values)[1:]:
            row = dict(zip(headers, values))
            if row.get("instance+.protocols.ospf.area+.interface+.name"):
                protocol_rows += 1
                assert row["instance+.@name"] in {
                    instance["name"]
                    for instance in expected[row["host"]]["routing_instances"]["instance"]
                }
        assert protocol_rows == 6
        for name in workbook.sheetnames:
            converter.process_by_sheet(workbook, name)
        assert converter.sheet_data == expected


class TestWriteBaseSheetData:
    """Tests for :meth:`ExcelToYaml.write_base_sheet_data`."""

    def test_creates_dest_dir_if_missing(self, tmp_path):
        """Output directory is created when it does not exist."""
        dest = str(tmp_path / "new_dir")
        e = ExcelToYaml("dummy.xlsx", dest)
        data = OrderedDict({
            "host.yaml": OrderedDict({"base": OrderedDict({"key": "val"})})
        })
        e.write_base_sheet_data(data, dest)
        assert os.path.isdir(dest)

    def test_writes_yaml_file(self, tmp_path):
        """A YAML file is written for each hostname entry."""
        dest = str(tmp_path)
        e = ExcelToYaml("dummy.xlsx", dest)
        data = OrderedDict({
            "host.yaml": OrderedDict({"base": OrderedDict({"key": "val"})})
        })
        e.write_base_sheet_data(data, dest)
        assert os.path.exists(os.path.join(dest, "host.yaml"))
