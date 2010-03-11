# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from ilog.application import (add_ctxnavbar_item, get_request, render_response)
from ilog.views.admin import render_admin_view
from ilog.i18n import _

def render_accounts_view(template_name, *args, **kwargs):
#    add_ctxnavbar_item('admin.accounts.index', _(u'Overview'))
    add_ctxnavbar_item('admin.accounts.groups', _(u'Groups'))
    add_ctxnavbar_item('admin.accounts.users', _(u'Users'))

    template_name = 'admin/accounts/%s' % template_name
    return render_admin_view(template_name, *args, **kwargs)


def index(request):
    return render_accounts_view('index.html')
