#!/bin/bash

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

# stop the script if a command fails
set -e

PACKAGE=yaml-to-excel
VERSION="21.7.0-1"

# cleanup version if the directory name is used
VTMP="${VERSION#$PACKAGE-}"
VERSION=${VTMP%/}


if [[ "x$VERSION" == "x" ]]; then
    echo "Must provide package version"
    exit 1
fi

if [ ! -d ${PACKAGE}-${VERSION} ]; then
    echo "Directory ${PACKAGE}-${VERSION} does not exist"
fi

rm -rf ${PACKAGE}-${VERSION}/etc
rm -rf ${PACKAGE}-${VERSION}/usr
rm -rf ${PACKAGE}-${VERSION}/lib
pip3 uninstall -y ${PACKAGE} || true
(cd ../..; PYTHONUSERBASE=$PWD/nita-${PACKAGE}/packaging/${PACKAGE}-${VERSION} pip3 install --user nita-${PACKAGE}/)

mkdir -p ${PACKAGE}-${VERSION}/usr/local
mv ${PACKAGE}-${VERSION}/bin ${PACKAGE}-${VERSION}/usr/local
mv ${PACKAGE}-${VERSION}/lib ${PACKAGE}-${VERSION}/usr/local
mv ${PACKAGE}-${VERSION}/usr/local/lib/python3.8/site-packages ${PACKAGE}-${VERSION}/usr/local/lib/python3.8/dist-packages

dpkg-deb --build ${PACKAGE}-${VERSION}
