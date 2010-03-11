# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from copy import copy
from bureaucracy.forms import *
from bureaucracy.forms import _next_position_hint
from bureaucracy.widgets import *

from ilog.utils import local
from ilog.application import get_request
from ilog.config import DEFAULT_VARS
from ilog.i18n import get_translations


def config_field(cfgvar, label=None, **kwargs):
    """Helper function for fetching fields from the config."""
    if isinstance(cfgvar, Field):
        field = copy(cfgvar)
    else:
        field = copy(DEFAULT_VARS[cfgvar])
    field._position_hint = _next_position_hint()
    if label is not None:
        field.label = label
    for name, value in kwargs.iteritems():
        setattr(field, name, value)
    return field

class Form(FormBase):
    csrf_protected = True
    redirect_tracking = False

    def _get_translations(self):
        return get_translations()

    def _lookup_request_info(self):
        """Called if no request info is passed to the form.  Might lookup
        the request info from a thread local storage.
        """
        return self._get_wsgi_environ()

    def _get_wsgi_environ(self):
        return get_request().environ

    def _autodiscover_data(self):
        """Called by `validate` if no data is provided.  Finds the
        matching data from the request object by default depending
        on the default submit method of the form.
        """
        return get_request().form

    def _get_session(self):
        return get_request().session

