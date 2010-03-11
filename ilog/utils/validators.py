# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import re
import logging
from ilog.database import User
from ilog.i18n import lazy_gettext, lazy_ngettext

from bureaucracy.forms import ValidationError

log = logging.getLogger(__name__)

_mail_re = re.compile(r'''(?xi)
    (?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+
        (?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|
        "(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|
          \\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@.
''')

def is_valid_email(form, value):
    """Check if the string passed is a valid mail address.

    >>> check(is_valid_email, 'somebody@example.com')
    True
    >>> check(is_valid_email, 'somebody AT example DOT com')
    False
    >>> check(is_valid_email, 'some random string')
    False

    Because e-mail validation is painfully complex we just check the first
    part of the email if it looks okay (comments are not handled!) and ignore
    the second.
    """
    if len(value) > 250 or _mail_re.match(value) is None:
        raise ValidationError(
            lazy_gettext(u'You have to enter a valid e-mail address.')
        )

def unique_username(form, username):
    if User.query.filter(User.username==username).first() is not None:
        raise ValidationError(
            lazy_gettext(u"The username \"%s\" is already taken.") %
            username
        )

def valid_username(form, username):
    log.debug("Checking for valid username %r", username)
    account = User.query.filter(User.username==username).first()
    if account is None:
        raise ValidationError(
            lazy_gettext(u"The username \"%s\" is not known.") %
            username
        )
    form.account = account

def unique_email(form, email):
    if User.query.filter(User.email==email).first() is not None:
        raise ValidationError(
            lazy_gettext(u"The email address \"%s\" is already registered with us.") %
            email
        )

def not_empty(form, value):
    """Make sure the value does consist of at least one
    non-whitespace character"""
    if not value.strip():
        raise ValidationError(lazy_gettext(u'The text must not be empty.'))

def is_netaddr(form, value):
    """Checks if the string given is a net address.  Either an IP or a
    hostname.  This currently does not support ipv6 (XXX!!)

    >>> check(is_netaddr, 'localhost')
    True
    >>> check(is_netaddr, 'localhost:443')
    True
    >>> check(is_netaddr, 'just something else')
    False
    """
    items = value.split()
    if len(items) > 1:
        raise ValidationError(
            lazy_gettext(u'You have to enter a valid net address.')
        )
    items = items[0].split(':')
    if len(items) not in (1, 2):
        raise ValidationError(
            lazy_gettext(u'You have to enter a valid net address.')
        )
    elif len(items) == 2 and not items[1].isdigit():
        raise ValidationError(lazy_gettext(u'The port has to be numeric'))
