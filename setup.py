#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import os
import sys

import setuptools

try:
    from platform import python_implementation as _pyimp
except (AttributeError, ImportError):
    def _pyimp():
        return 'Python (unknown)'

NAME = 'django_periodiq'

# -*- Python Versions -*-
PYIMP = _pyimp()
PY26_OR_LESS = sys.version_info < (2, 7)
PY3 = sys.version_info[0] == 3
PY34_OR_LESS = PY3 and sys.version_info < (3, 5)
PYPY_VERSION = getattr(sys, 'pypy_version_info', None)
PYPY = PYPY_VERSION is not None
PYPY24_ATLEAST = PYPY_VERSION and PYPY_VERSION >= (2, 4)

# -*- Requirements -*-


def _strip_comments(l):
    return l.split('#', 1)[0].strip()


def _pip_requirement(req):
    if req.startswith('-r '):
        _, path = req.split()
        return reqs(*path.split('/'))
    return [req]


def _reqs(*f):
    return [
        _pip_requirement(r) for r in (
            _strip_comments(l) for l in open(
                os.path.join(os.getcwd(), 'requirements', *f)).readlines()
        ) if r]


def reqs(*f):
    """Parse requirement file.
    Example:
        reqs('default.txt')          # requirements/default.txt
        reqs('extras', 'redis.txt')  # requirements/extras/redis.txt
    Returns:
        List[str]: list of requirements specified in the file.
    """
    return [req for subreq in _reqs(*f) for req in subreq]


def extras(*p):
    """Parse requirement in the requirements/extras/ directory."""
    return reqs('extras', *p)


def install_requires():
    """Get list of requirements required for installation."""
    return reqs('default.txt')

# -*- Long Description -*-


def long_description():
    try:
        return codecs.open('README.rst', 'r', 'utf-8').read()
    except IOError:
        return 'Long description error: Missing README.rst file'

# -*- Command: setup.py test -*-


setuptools.setup(
    name=NAME,
    packages=setuptools.find_packages(exclude=['t', 't.*']),
    version='0.0.1a',
    description='Django Periodiq',
    long_description=long_description(),
    author='slav',
    author_email='',
    url='',
    license='BSD',
    platforms=['any'],
    install_requires=install_requires(),
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'periodiq = periodiq.__main__:main',
        ],
    },
)
