# -*- coding: utf-8 -*-
"""
    _init_zine
    ~~~~~~~~~~

    Helper to locate zine and the instance folder.

    :copyright: (c) 2010 by the Zine Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from os.path import abspath, join, dirname, pardir, isfile
import sys

# set to None first because the installation replaces this
# with the path to the installed zine library.
ILOG_LIB = None

if ILOG_LIB is None:
    ILOG_LIB = abspath(join(dirname(__file__), pardir))

# make sure we load the correct zine
sys.path.insert(0, ILOG_LIB)


def find_instance(instance=None):
    """Find the Zine instance."""
    if isfile(join('instance', 'ilog.ini')):
        instance = abspath('instance')
    else:
        old_path = None
        path = abspath('.')
        while old_path != path:
            path = abspath(join(path, pardir))
            if isfile(join(path, 'ilog.ini')):
                instance = path
                break
            old_path = path
    return instance
