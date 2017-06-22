#!/usr/bin/python

import sys
import os
from setuptools import setup


NAME = 'saasherder'


def get_requirements():
    with open('requirements.txt') as fd:
        return fd.read().splitlines()


def get_version():
    with open(os.path.join(NAME, 'version.py')) as f:
        version = f.readline()
    # dirty, remove trailing and leading chars
    return version.split(' = ')[1][1:-2]

setup(
    name=NAME,
    version=get_version(),
    packages=[NAME],
    install_requires=get_requirements(),
    author='Vaclav Pavlin',
    author_email='vasek@redhat.com',
    maintainer='Vaclav Pavlin',
    maintainer_email='vasek@redhat.com',
    description='OpenShift deployment version tracking tool',
    url='https://github.com/openshiftio/saas',
    license='BSD',
    entry_points = {
              'console_scripts': [
                  'saasherder = saasherder.cli:main',                  
              ],              
          },
)