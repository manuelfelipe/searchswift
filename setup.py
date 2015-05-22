#!/usr/bin/python
# Copyright (c) 2015 YP Canada.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup, find_packages
import shutil
import sys

name = 'searchswift'
version = '0.1'

setup(
    name=name,
    version=version,
    description='Search Swift Metadata - Swift Middleware',
    license='Apache License (2.0)',
    author='Manuel Correa',
    author_email='manuel.correa@yp.ca',
    url='http://yp.ca',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Environment :: No Input/Output (Daemon)',
        ],
    install_requires=[],
    entry_points={
        'paste.app_factory': ['main=identity:app_factory'],
        'paste.filter_factory': [
            'searchmiddleware=searchswift.middleware:filter_factory',
            ],
        },
    )

cmdline = ''.join(sys.argv[1:])
if 'clean' in cmdline:
    shutil.rmtree('projectname.egg-info', ignore_errors=True)