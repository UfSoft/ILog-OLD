# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from ilog.application import (get_request, render_response, url_for,
                              add_metanav_item, add_navbar_item)
from ilog.database import Channel
from ilog.i18n import _
from ilog.privileges import ILOG_ADMIN, ENTER_ADMIN_PANEL, ENTER_ACCOUNT_PANEL

#def render_view(template_name, _active_menu_item='network.index', **values):
#    """Works pretty much like the normal `render_response` function but
#    it emits some events to collect navigation items and injects that
#    into the template context. This also gets the flashes messages from
#    the user session and injects them into the template context after the
#    plugins have provided theirs in the `before-admin-response-rendered`
#    event.
#
#    The second parameter can be the active menu item if wanted. For example
#    ``'options.overview'`` would show the overview button in the options
#    submenu. If the menu is a standalone menu like the dashboard (no
#    child items) you can also just use ``'dashboard'`` to highlight that.
#    """
#    request = get_request()
#
#    # setup metanav
##    if request.user.has_privilege(ENTER_ACCOUNT_PANEL):
#    if request.user.is_somebody:
#        metanav = [
#            ('account', 'account.logout', _("logout (%s)") % request.user.username),
#            ('account', 'account.dashboard', _("My Account"))
#        ]
#    else:
#        metanav = [
#            ('account', 'account.login', _("Login")),
#        ]
#
#    if request.user.has_privilege(ILOG_ADMIN):
#        metanav.append(('admin', 'admin.index', _("Administration")))
#
#    metanav.extend(request.metanav)
#
#
#    # set up the navigation bar
#    navigation_bar = [
#        ('network', 'network.index', _('Networks'), [
#            ('index', 'network.index', _('Browse Networks')),
##            ('channels', 'network.channels', _('Browse Channels'))
#        ])
#    ]
#    navigation_bar.extend(request.navbar)
#
#    # find out which is the correct menu and submenu bar
#    active_menu = active_submenu = None
#    _active_item = _active_menu_item and _active_menu_item or request.endpoint
#    if _active_item is not None:
#        p = _active_item.split('.')
#        if len(p) == 1:
#            active_menu = active_submenu = p[0]
#        else:
#            active_menu, active_submenu = p
#    for menu_item, view, title, subnavigation_bar in navigation_bar:
#        print 12345, active_menu, menu_item, view, title
#        if menu_item == active_menu:
#            break
#    else:
#        subnavigation_bar = []
#
#    # if we are in maintenance_mode the user should know that, no matter
#    # on which page he is.
##    if request.app.cfg['maintenance_mode'] and \
##                                        request.user.has_privilege(BLOG_ADMIN):
##        flash(_(u'ILog is in maintenance mode. Don\'t forget to '
##                u'turn it off again once you finish your changes.'))
#
#    # the admin variables is pushed into the context after the event was
#    # sent so that plugins can flash their messages. If we would emit the
#    # event afterwards all flashes messages would appear in the request
#    # after the current request.
#    values['core'] = {
#        'metanav': [{'id':    view,
#                     'url':   url_for(view),
#                     'title': title,
#                     'active': active_menu == menu_item
#                     } for menu_item, view, title in metanav],
#        'navbar': [{'id':       view,
#                    'url':      url_for(view),
#                    'title':    title,
#                    'active':   active_menu == menu_item
#                    } for menu_item, view, title, children in navigation_bar],
#        'ctxnavbar': [{'id':       view,
#                       'url':      url_for(view),
#                       'title':    title,
#                       'active':   active_submenu == submenu_item
#                       } for submenu_item, view, title in subnavigation_bar],
#        'messages': [{
#            'type':     type,
#            'msg':      msg
#        } for type, msg in request.session.pop('flashed_messages', [])],
#        'active_pane': _active_menu_item
#    }
#    return render_response(template_name, **values)

def index(request):
    channels_count = Channel.query.count()
    return render_response('index.html', channels_count=channels_count)
