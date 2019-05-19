# -*- coding: utf-8 -*-
"""``Stick`` setup tools file."""

from setuptools import setup

setup(
    name='stick',
    version='0.0.1',
    description='The Stick of Truth',
    author='Kristoffer Nilsson',
    author_email='smrt@novafaen.se',
    url='http://smrt.novafaen.se/',
    packages=['stick'],
    install_requires=[
        'smrt',
        'requests'
    ],
    dependency_links=[
        'git+https://github.com/novafaen/smrt.git#egg=smrt'
    ],
    test_suite='tests'
)
