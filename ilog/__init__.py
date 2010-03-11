# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

"""
IRC Logging
===========

Opt-In online IRC logging for the masses.
"""

__version__     = '0.1'
__package__     = 'ILog'
__summary__     = "Online IRC logging for the masses."
__author__      = 'Pedro Algarvio'
__email__       = 'ufs@ufsoft.org'
__license__     = 'BSD'
__url__         = 'https://hg.ufsoft.org/ILog'
__description__ = __doc__

# implementation detail.  Stuff in __all__ and the initial import has to be
# the same.  Everything that is not listed in `__all__` or everything that
# does not start with two leading underscores is wiped out on reload and
# the core module is *not* reloaded, thus stuff will get lost if it's not
# properly listed.
from ilog._core import setup, get_wsgi_app, override_environ_config
__all__ = ('setup', 'get_wsgi_app', 'override_environ_config')
