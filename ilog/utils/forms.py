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
from bureaucracy.utils import fill_dict, set_fields, _missing as missing

from ilog.utils import local
from ilog.application import get_request, url_for
from ilog.config import DEFAULT_VARS
from ilog.database import db
from ilog.i18n import get_translations, lazy_gettext
from ilog.utils.http import redirect


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

    def _resolve_url(self, args, kwargs):
        return url_for(*args, **kwargs)

    def _redirect_to_url(self, url):
        return redirect(url)


class ModelField(Field):
    """A field that queries for a model.

    The first argument is the name of the model, the second the named
    argument for `filter_by` (eg: `User` and ``'username'``).  If the
    key is not given (None) the primary key is assumed.
    """
    messages = dict(not_found=lazy_gettext(u'“%(value)s” does not exist'))

    def __init__(self, model, key=None, label=None, help_text=None,
                 required=False, message=None, validators=None, widget=None,
                 messages=None, on_not_found=None):
        Field.__init__(self, label, help_text, validators, widget, messages)
        self.model = model
        self.key = key
        self.required = required
        self.message = message
        self.on_not_found = on_not_found

    def convert(self, value):
        if isinstance(value, self.model):
            return value
        if not value:
            if self.required:
                raise ValidationError(self.messages['required'])
            return None
        value = self._coerce_value(value)

        if self.key is None:
            rv = self.model.query.get(value)
        else:
            rv = self.model.query.filter_by(**{self.key: value}).first()

        if rv is None:
            if self.on_not_found is not None:
                self.on_not_found(value)
            raise ValidationError(self.messages['not_found'] %
                                  {'value': value})
        return rv

    def _coerce_value(self, value):
        return value

    def to_primitive(self, value):
        if value is None:
            return u''
        elif isinstance(value, self.model):
            if self.key is None:
                value = db.class_mapper(self.model) \
                          .primary_key_from_instance(value)[0]
            else:
                value = getattr(value, self.key)
        return unicode(value)


class HiddenModelField(ModelField):
    """A hidden field that points to a model identified by primary key.
    Can be used to pass models through a form.
    """
    widget = HiddenInput

    # these messages should never show up unless ...
    #   ... the user tempered with the form data
    #   ... or the object went away in the meantime.
    messages = dict(
        invalid=lazy_gettext('Invalid value.'),
        not_found=lazy_gettext('Key does not exist.')
    )

    def __init__(self, model, key=None, required=False, message=None,
                 validators=None, widget=None, messages=None,
                 default=missing):
        ModelField.__init__(self, model, key, None, None, required,
                            message, validators, widget, messages,
                            default)

    def _coerce_value(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(self.messages['invalid'])
