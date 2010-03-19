# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from ilog.application import (add_ctxnavbar_item, add_navbar_item, get_request,
                              get_application, render_response)
from ilog.i18n import _
from ilog.privileges import require_privilege, ILOG_ADMIN

def render_admin_view(*args, **kwargs):
    add_navbar_item('admin.index', _(u'Dashboard'))
    add_navbar_item('admin.manage.groups', _(u'Manage'))
    add_navbar_item('admin.options.basic', _(u'Options'))
    return render_response(*args, **kwargs)


@require_privilege(ILOG_ADMIN)
def index(request):
    return render_admin_view('admin/index.html')
