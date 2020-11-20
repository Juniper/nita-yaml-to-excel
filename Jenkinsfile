#!groovy

/* ********************************************************

Project: nita-yaml-to-excel
Version: 20.10

Copyright (c) Juniper Networks, Inc., 2020. All rights reserved.

Notice and Disclaimer: This code is licensed to you under the Apache 2.0 License (the "License"). You may not use this code except in compliance with the License. This code is not an official Juniper product. You can obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0.html

SPDX-License-Identifier: Apache-2.0

Third-Party Code: This code may depend on other components under separate copyright notice and license terms. Your use of the source code for those components is subject to the terms and conditions of the respective license as noted in the Third-Party source code file.

******************************************************** */

@Library('PS-Shared-libs') _

node('master') {
    try {
        stage('Checkout'){
            checkout scm
        }
        withDockerRegistry(credentialsId: 'ps-ci', toolName: 'master', url: 'https://ps-docker-internal.artifactory.aslab.juniper.net') {
            docker.image('ps-docker-internal.artifactory.aslab.juniper.net/py-builder:latest').inside('-u root') {
                stage('Cleanup'){
                    echo 'cleanup'
                    sh 'rm -rf dist'
                    sh 'rm -rf .pypirc'
                }
                stage('Test'){
                    echo 'Running unit tests'
                    sh 'python3 setup.py test'
                    ciSkip action: 'check'
                }
                stage('Install'){
                    echo 'Running a test installation'
                    sh 'pip3 install .'
                    ciSkip action: 'check'
                }
                stage('Publish'){
                    if (env.SOURCE_BRANCH == 'refs/heads/master') {
                        echo 'Push to Artifactory'
                        sh 'python3 setup.py sdist'
                        withCredentials([file(credentialsId:'f1503ca7-3285-4ac6-ae55-5a660658c075', variable: 'PYPIRC')]) {
                            sh 'ln -s $PYPIRC $HOME/.pypirc'
                            sh 'python3 setup.py sdist upload -r local'
                        }
                    }
                    else {
                        echo "Only the master branch is published to the repository"
                    }
                }
                stage('Test pull'){
                    if (env.SOURCE_BRANCH == 'refs/heads/master') {
                        echo 'Pull from Artifactory'
                        sh 'pip3 install -i https://artifactory.aslab.juniper.net/artifactory/api/pypi/ps-pypi/simple yaml-to-excel'
                    }
                }
            }
        }
    }
    finally {
        ciSkip action: 'postProcess'
    }
}
