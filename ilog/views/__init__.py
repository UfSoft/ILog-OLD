# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from ilog.views import account, admin, base, networks
from ilog.views.admin import options
from ilog.views.admin.manage import users, groups

all_views = {
    # Main Handler
    'index'             : base.index,

    # Account Handlers
    'account.login'     : account.login,
    'account.logout'    : account.logout,
    'account.profile'   : account.profile,
    'account.dashboard' : account.dashboard,
    'account.register'  : account.register,
    'account.rpx'       : account.rpx_post,
    'account.activate'  : account.activate_account,

    # Network Handlers
    'network.index'     : networks.index,
    'network.channels'  : networks.channels,

    # Channel Handlers
    'channel.index'     : '',
    'channel.browse'    : '',

    # Administration
    'admin.index'                   : admin.index,
    'admin.manage.groups'           : groups.list,
    'admin.manage.groups.new'       : groups.edit,
    'admin.manage.groups.edit'      : groups.edit,
    'admin.manage.groups.delete'    : groups.delete,
    'admin.manage.users'            : users.list,
    'admin.manage.users.new'        : users.edit,
    'admin.manage.users.edit'       : users.edit,
    'admin.manage.users.delete'     : users.delete,
    'admin.options.basic'           : options.basic_options,
    'admin.options.advanced'        : options.advanced_options,
    'admin.options.rpxnow'          : options.rpxnow_options,
    'admin.options.gravatar'        : options.gravatar_options,
    'admin.options.email'           : options.email_options,
    'admin.options.cache'           : options.cache_options,
}
