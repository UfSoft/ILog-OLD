# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import unicodedata

from werkzeug.local import Local, LocalManager
from werkzeug.utils import html as h, escape
from ilog.i18n import _
from ilog.utils import htmlhelpers as h


# our local stuff
local = Local()
local_manager = LocalManager([local])


def flash(msg, type='info'):
    """Add a message to the message flash buffer.

    The default message type is "info", other possible values are
    "add", "remove", "error", "ok" and "configure". The message type affects
    the icon and visual appearance.

    The flashes messages appear only in the admin interface!
    """
    assert type in \
        ('info', 'add', 'remove', 'error', 'ok', 'configure', 'warning')
    if type == 'error':
        msg = (u'<strong>%s:</strong> ' % _('Error')) + escape(msg)
    if type == 'warning':
        msg = (u'<strong>%s:</strong> ' % _('Warning')) + escape(msg)

    local.request.session.setdefault('flashed_messages', []).\
            append((type, msg))

def gen_ascii_slug(text, delim=u'-'):
    if isinstance(text, unicode):
        text = text.decode('utf-8', 'replace')
    text = delim.join(text.split())
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')
