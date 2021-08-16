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

#if [ $UID != 0 ]; then
#	echo "This script must be run as root"
#        exit 1
#fi

# stop the script if a command fails
set -e

PACKAGE=yaml-to-excel
VERSION="21.7.0"
RELEASE="1"

#yum install -yy epel-release
sudo yum install -yy python3 #python36-PyYAML python3-pip
sudo yum install -yy rpm-build

# cleanup version if the directory name is used
VTMP="${VERSION#$PACKAGE-}"
VERSION=${VTMP%/}


if [[ "x$VERSION" == "x" ]]; then
    echo "Must provide package version"
    exit 1
fi

if [ ! -d ${PACKAGE}-${VERSION}-${RELEASE} ]; then
    echo "Directory ${PACKAGE}-${VERSION}-${RELEASE} does not exist"
fi

export SOURCE_DIR=${PACKAGE}-${VERSION}-${RELEASE}/SOURCES

# clear the source dir of /usr (leave /etc)
rm -rf ${SOURCE_DIR}/${PACKAGE}-${VERSION}/usr
pip3 uninstall -y ${PACKAGE} || true
(cd ../..; PYTHONUSERBASE=$PWD/nita-${PACKAGE}/packaging_redhat/${SOURCE_DIR}/${PACKAGE}-${VERSION} pip3 install --user nita-${PACKAGE}/)

mkdir -p ${SOURCE_DIR}/${PACKAGE}-${VERSION}/usr/local
mv ${SOURCE_DIR}/${PACKAGE}-${VERSION}/bin ${SOURCE_DIR}/${PACKAGE}-${VERSION}/usr/local
mv ${SOURCE_DIR}/${PACKAGE}-${VERSION}/lib ${SOURCE_DIR}/${PACKAGE}-${VERSION}/usr/local
#mv ${SOURCE_DIR}/${PACKAGE}-${VERSION}/usr/local/lib/python3.6/site-packages ${SOURCE_DIR}/${PACKAGE}-${VERSION}/usr/local/lib/python3.6/dist-packages

# Create a tarball of with source
(
    cd ${SOURCE_DIR}
    tar czf ${PACKAGE}-${VERSION}.tar.gz ${PACKAGE}-${VERSION}
)

# Build rpm file
export RPM_BUILD_DIR="${PWD}/${PACKAGE}-${VERSION}-${RELEASE}"
cp .rpmmacros ~
rpmbuild -ba ${PACKAGE}-${VERSION}-${RELEASE}/SPECS/${PACKAGE}.spec
