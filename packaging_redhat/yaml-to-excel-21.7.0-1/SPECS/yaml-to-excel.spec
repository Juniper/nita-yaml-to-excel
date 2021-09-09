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

%define        __spec_install_post %{nil}
%define          debug_package %{nil}
%define        __os_install_post %{_dbpath}/brp-compress

Name:           yaml-to-excel
Version:        21.7.0
Release:        1
Summary:        Tool for converting excel spreadsheets to and from yaml
Group:          Development/Tools
BuildArch:      x86_64
License:        Apache License, Version 2.0, http://www.apache.org/licenses/LICENSE-2.0
URL:            https://www.juniper.net
Source0:        %{name}-%{version}.tar.gz
Requires:       python3

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

%description
Tool for converting excel spreadsheets to and from yaml.  Includes yaml2xls.py and xls2yaml.py.

%pre
# Empty section.

%prep
%setup -q

%build
# Empty section.

%install
rm -rf %{buildroot}
mkdir -p  %{buildroot}
# in builddir
cp -a * %{buildroot}

%clean
rm -rf %{buildroot}

%post
# Empty section.

%preun
# Empty section.

%files
%defattr(-,root,root,-)
%{_prefix}/local/bin/*
%{_prefix}/local/lib/*
%{_sysconfdir}/profile.d/yaml-to-excel.sh

%changelog
* Fri Aug 13 2021 Ashley Burston 21.7.0-1
  - Got rid of xlwt and xlrd
* Wed Jul 29 2020 Hugo Ribeiro 1.0.0-1
  - Bug fixes
* Wed May 6 2020 Ashley Burston 0.9.0-1
  - Initial rpm release
