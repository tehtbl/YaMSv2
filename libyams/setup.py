# -*- coding: utf-8 -*-
#
#    Copyright (C) 2017  https://github.com/tbl42
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
from setuptools import setup, find_packages

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='LibYaMS',
    version='0.2.0-dev',
    # packages=find_packages(),
    # packages=find_packages('libyams'),
    packages=['libyams'],
    install_requires=[
        'python-telegram-bot==7.0.1',
        'requests==2.20.0',
        'wrapt==1.10.11',
        'PyYAML==3.11',
        'Django==1.11.29'
    ],
    author='tbl42',
    author_email='3999809+tbl42@users.noreply.github.com',
    url='https://not-yet-defined/',
    description='lib for YaMS',
    keywords='',

    license='see LICENSE',
    long_description=open('README.md').read(),

    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Unknown',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
    ]
)
