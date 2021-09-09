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


one_level_hierarchy_simple_dict = """
protocol_hashes:
    bgp: $eqweoz36
    ebgp: $9eqweqwewqdqwdqwd
    ospf: $wqewqewqawdrv69rvWLVb.P5
    rsvp: $721993$DPjmT6---q12312w1ed1asdbaZUj.PTz39tu
"""

simple_struct = """
build_dir: /var/tmqwrewqewqp/build/{qewwqdwqd{ inventory_hostname }}/tmp
xml_dir: /var/tmpfwqwqwqweqw
junos_conf: /var/tmp/build/{{ inventory_hostname }}/junos.conf
netconf_port: 22
netconf_user: nee2131e21dwtad21321312n
netconf_passwd: p2213e21321
OS_dir: /var/tm/junos_os
log: /var/
wait_time: 800
absent_port_wait: 20
"""

Simple_list = """
ftp:
  - 10.99.0.134
  - 10.0.2.5
  - 10.10.72.184
"""

one_level_herarchy_with_list = """
ntp:
  servers:
    - 10.99.0.134
    - 10.0.2.5
    - 10.10.72.184
  boot_server: 10.1.10.134
"""

two_level_hierarchy_with_nested_list = """
snmp:
  location: "NGCN, LO4Y, 5,Chennai"
  contact: "KBS Global"
  communities:
    - name: SKCpolling
      clients:
        - 192.168.0.0/16
        - 10.1.0.53/32
        - 192.168.5.197/32
        - 192.168.8.60/32
        - 10.10.7.2/32
    - name: fx12312sws
      clients:
        - 192.168.0.0/16
        - 192.168.90.53/32
        - 10.10.0.197/32
        - 10.10.0.61/32
        - 10.10.73.254/32
"""
two_level_hierarchy_with_nested_list_within_nested_list = """
snmp:
  location: "NGCN, LO4Y, 5,Chennai"
  contact: "KBS Global"
  communities:
    - name: SKCpolling
      -clients:
        - 192.168.0.0/16
        - 10.1.0.53/32
        - 192.168.5.197/32
        - 192.168.8.60/32
        - 10.10.7.2/32
      -clients:
        - 192.168.0.1/16
        - 10.1.0.54/32
        - 192.168.3.197/32
        - 192.168.2.60/32
        - 10.10.7.4/32
    - name: fx12312sws
      -clients:
        - 192.168.0.0/16
        - 192.168.90.53/32
        - 10.10.0.197/32
        - 10.10.0.61/32
        - 10.10.73.254/32
"""

# Three level hierarchy is not supported.
three_level_hierarchy_with_nested_list_within_nested_list = """
Snmp:
  location: "NGCN, LO4Y, 5,Chennai"
  contact: "KBS Global"
  communities:
     - name: SKCpolling
       clients:
         - Client1: 10.1.0.53/32
           ports:
               - 8080
               - 8081
         - Client2: 10.1.0.52/32
           ports:
               - 8080
               - 8081
"""
three_level_hierarchy_with_nested_list_within_nested_list_with_dict_values = """
Snmp:
  location: "NGCN, LO4Y, 5,Chennai"
  contact: "KBS Global"
  communities:
     - name: SKCpolling
       clients:
         - Client1: 10.1.0.53/32
           ports:
               - port1: 8080
                 port2: 8081
         - Client2: 10.1.0.52/32
           ports:
               - port1: 8080
                 port2: 8081
"""
three_level_hierarchy_with_nested_list_within_nested_list_with_nest_list = """
Snmp:
  location: "NGCN, LO4Y, 5,Chennai"
  contact: "KBS Global"
  communities:
     - name: SKCpolling
       clients:
         - Client1: 10.1.0.53/32
           ports:
               - name:
                   - port1: 8080
                     port2: 8081
               - name:
                   - port1: 80862
                     port2: 80813
         - Client2: 10.1.0.52/32
           ports:
               - name:
                   - port1: 8080
                     port2: 8081
"""
three_level_combo = """
tenants:
  - name: TS001-TRAC
    irbs:
      - irb: 402
    protocols:
      - protocol: tgr
        groups:
          - group: EBGP-INS-SRX-UCAST
            imports:
              - import: IMP-INES-ROUTES
              - import: PL-DNY-AL
  - name: T026-GGUZ
    aes:
      - ae: 35
    irbs:
      - irb: 241
    dhcp_relay:
      server_groups:
        - group: WIRELESS-DHCP
          addresses:
            - address: 192.168.27.2
      groups:
        - group: DHCP-WIRED
          active_svr_group: WIRED-DHCP
          irb: 14 96
          type: 187
    protocols:
      - protocol: vim
        static_rp: 192.168.27.1
      - protocol: tgr
        groups:
          - group: EBEGP-KO4S-ITS
            exports:
              - export: PLIT-ITES-DEFAULT-EXPORT
"""
one_level_hierarchy_with_nested_list = """
trap:
    - name: SART
      targets:
        - 192.168.0.15
        - 192.168.0.11
    - name: space
      version: v2
      targets:
        - 192.168.1.105
        - 192.168.2.105
"""
one_level_hierarchy_with_nested_list = """
trap:
    - name: SART
      targets:
        - 192.168.0.15
        - 192.168.0.11
    - name: space
      version: v2
      targets:
        - 192.168.1.105
        - 192.168.2.105
"""
one_level_hierarchy_with_nested_list_with_dict = """
trap:
    SNMP:v3
    - name: SART
      targets:
        - 192.168.0.15
        - 192.168.0.11
    - name: space
      version: v2
      targets:
        - 192.168.1.105
        - 192.168.2.105
"""
one_level_hierarchy_with_nested_list_with_dict_values = """
groups:
        - group: DHCP-WIRED
          active_group: WIRED-DHCP
          interfaces:
            - irb: irb.508
            - irb: irb.510
            - irb: irb.1000
        - group: DHCP-WIRELESS
          active_group: WIRELESS-DHCP
          interfaces:
            - irb: irb.500
            - irb: irb.520
            - irb: irb.521
"""

two_level_hierarchy_with_dict_values_in_nested_list = """
protocol_ospf:
  areas:
    - area: 0.0.0.0
      interfaces:
        - int: lo0.0
          passive:
        - int: ae0.192
"""

one_level_hierarchy_with_dict_values_in_list = """
interfaces:
  - int: xe-2/0/0
    desc: fn=crtj-lo4y-1001 di=xe-2/0/0
    ae: 0
  - int: xe-2/1/0
    desc: fn=crtj-lo4y-1001 di=xe-2/1/0
    ae: 0
  - int: xe-2/0/1
    desc: fn=SVL dd=cwca-lo4y-0001 di=pc2
    ae: 1
"""
complex_list_with_integers = """
test_interface_rota:
  start:
    fpc: 0
    mic: 0
    pic: 4
    next_fpc:
      - 0
      - 6
      - 1
      - 7
    last_pic: 8
  wrap:
    fpc: 0
    mic: 4
    pic: 0
  restart:
    fpc: 2
    mic: 0
    pic: 4
    next_fpc:
      - 2
      - 8
      - 3
      - 9
    last_pic: 8
"""


@ddt
class ParserTestCase(unittest.TestCase):

    def tearDown(self):
        yaml_file = 'test.yaml'
        xls_file = 'all.xlsx'
        try:
            os.remove(xls_file)
            os.remove(yaml_file)
        except OSError:
            pass

    @data(one_level_herarchy_with_list,
          simple_struct,
          Simple_list,
          one_level_herarchy_with_list,
          one_level_hierarchy_with_nested_list,
          two_level_hierarchy_with_nested_list,
          one_level_hierarchy_with_dict_values_in_list,
          two_level_hierarchy_with_dict_values_in_nested_list,
          one_level_hierarchy_with_nested_list_with_dict_values,
          two_level_hierarchy_with_nested_list_within_nested_list,
          three_level_hierarchy_with_nested_list_within_nested_list,
          three_level_hierarchy_with_nested_list_within_nested_list_with_dict_values,
          three_level_hierarchy_with_nested_list_within_nested_list_with_nest_list,
          three_level_combo,
          complex_list_with_integers
          )
    def testSimpleStruct(self, value):
        ini_cont = yaml.load(value)
        with open('test.yaml', 'w') as outfile:
            outfile.write(
                yaml.dump(ini_cont, default_flow_style=False, explicit_start=True))
        yaml2xls_instance = yaml2xls.YamlToExcel(['test.yaml'])
        yaml2xls_instance.convert_data()
        xls2yaml_instance = xls2yaml.ExcelToYaml('all.xlsx', './')
        xls2yaml_instance.convert_data()
        final_cont = yaml.load(open('test.yaml', 'r'))
        self.assertDictEqual(ini_cont, final_cont)


def runTests():
    suite = unittest.makeSuite(ParserTestCase, 'test')
    runner = unittest.TextTestRunner(verbosity=2, failfast=True)
    runner.run(suite)


if __name__ == '__main__':
    runTests()
