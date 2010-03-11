# -*- coding: utf-8 -*-
"""
    ilog.environment
    ~~~~~~~~~~~~~~~~

    :copyright: (c) 2010 by the Zine Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from os.path import realpath, dirname, join, pardir, isdir

# the path to the contents of the zine package
PACKAGE_CONTENTS = realpath(dirname(__file__))

# the path to the folder where the "zine" package is stored in.
PACKAGE_LOCATION = realpath(join(PACKAGE_CONTENTS, pardir))

# name of the domain for the builtin translations
LOCALE_DOMAIN = 'messages'


SHARED_DATA = join(PACKAGE_CONTENTS, 'shared')


TEMPLATE_PATH = join(PACKAGE_CONTENTS, 'templates')

# Localisation catalogs location
LOCALE_PATH = join(PACKAGE_CONTENTS, 'locale')

# get rid of the helpers
del realpath, dirname, join, pardir, isdir
