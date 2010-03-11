# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from ilog.i18n import _
from ilog.application import add_ctxnavbar_item, get_request, render_response

def render_network_view(*args, **kwargs):
##    request = get_request()
##    request.navbar.append(
##        ('network', 'account.dashboard', _(u'Networks'), [
##            ('index', 'account.dashboard', _(u'Browse Networks')),
##        ])
##    )
#    return render_view(*args, **kwargs)
    add_ctxnavbar_item('network.index', _('Browse Networks'))
    add_ctxnavbar_item('network.index2', _('Browse Networks'))
    return render_response(*args, **kwargs)

def index(request):
    return render_network_view('index.html')

def channels(request):
    return render_network_view('index.html')
