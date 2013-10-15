#!/usr/bin/env python

import os.path
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setupconf = dict(
    name = 'djony',
    version = "0.0.1",
    license = 'LGPL',
    url = 'https://github.com/nnseva/djony/',
    author = 'Vsevolod Novikov',
    author_email = 'nnseva@gmail.com',
    description = ('Pony ORM to Django integration library'),
    long_description = read('README.rst'),

    packages = find_packages(),

    install_requires = ['pony>=0.4.8'],

    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: LGPL License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        ],
    )

if __name__ == '__main__':
    setup(**setupconf)
