# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from ilog.i18n import lazy_gettext, list_languages, list_timezones
from bureaucracy.forms import (ChoiceField, CommaSeparated, TextField,
                               BooleanField, IntegerField)
from ilog import __summary__
from ilog.utils.validators import is_valid_email, is_netaddr

l_ = lazy_gettext   # shortcut

class DefaultValueMixin(object):

    def __init__(self, *args, **kwargs):
        self._default = kwargs.pop('default', None)
        super(DefaultValueMixin, self).__init__(*args, **kwargs)

    def get_default(self):
        if callable(self._default):
            return self._default()
        return self._default

class DChoiceField(DefaultValueMixin, ChoiceField):
    pass

class DCommaSeparated(DefaultValueMixin, CommaSeparated):
    pass

class DTextField(DefaultValueMixin, TextField):
    pass

class DBooleanField(DefaultValueMixin, BooleanField):
    pass

class DIntegerField(DefaultValueMixin, IntegerField):
    pass

DEFAULT_VARS = {
    'database_uri':             DTextField(default=u'',
        label=l_(u'Database URI'), help_text=l_(
        u'The database URI.  For more information about database settings '
        u'consult the Zine help.')),
    'database_debug':           DBooleanField(default=False, help_text=l_(
        u'If enabled, the database will collect all SQL statements and add '
        u'them to the bottom of the page for easier debugging.')),
    'cookie_name':              DTextField(default=u'ilog_session',
        help_text=l_(u'If there are multiple Zine installations on '
        u'the same host, the cookie name should be set to something different '
        u'for each blog.')),
    'secret_key':               DTextField(default=u'', help_text=l_(
        u'The secret key is used for various security related tasks in the '
        u'system.  For example, the cookie is signed with this value.')),
    'ilog_url':                 DTextField(default=u'', help_text=l_(
        u'The base URL of the blog.  This has to be set to a full canonical URL'
        u' (including http or https).  If not set, the application will behave '
        u'confusingly.  Remember to change this value if you move your blog '
        u'to a new location.')),
    'ilog_email':               DTextField(default=u'', help_text=l_(
        u'The email address given here is used by the notification system to '
        u'send emails from.  Also plugins that send mails will use this address'
        u' as the sender address.'), validators=[is_valid_email]),
    'maintenance_mode':         DBooleanField(default=False, help_text=l_(
        u'If enabled, only administrator will be able to use ILog, all other '
        u'user will see a nice message stating the ILog is not available at '
        u'the moment.')),
    'timezone':                 DChoiceField(choices=sorted(list_timezones()),
                                             default=u'UTC', help_text=l_(
        u'The timezone of the blog.  All times and dates in the user interface '
        u'and on the website will be shown in this timezone.  It\'s save to '
        u'change the timezone after posts are created because the information '
        u'in the database is stored as UTC.')),
    'language':                 DChoiceField(choices=list_languages(),
                                             default=u'en', help_text=l_(
        u'The default ILog language. Users will have the choice to choose the '
        u'language, from the available ones, the one their desire.')),
    # RPXNow.com settings
    'rpxnow/app_domain':        DTextField(default=u'', help_text=l_(
        u'The RPXNow.com application domain.')),
    'rpxnow/api_key':           DTextField(default='', help_text=l_(
        u'The RPXNow.com API key.')),

    # cache settings
    'enable_eager_caching':     DBooleanField(default=False),
    'cache_timeout':            DIntegerField(default=300, min_value=10),
    'cache_system':             DChoiceField(choices=[
        (u'null', l_(u'No Cache')),
        (u'simple', l_(u'Simple Cache')),
        (u'memcached', l_(u'memcached')),
        (u'filesystem', l_(u'Filesystem'))
    ], default='null'),
    'memcached_servers':        DCommaSeparated(DTextField(
                                                    validators=[is_netaddr],
                                               ), default=list),
    'filesystem_cache_path':    DTextField(default=u'cache'),

    # email settings
    'smtp_host':                DTextField(default=u'localhost'),
    'smtp_port':                DIntegerField(default=25),
    'smtp_user':                DTextField(default=u''),
    'smtp_from_name':           DTextField(default=u'Ilog'),
    'smtp_password':            DTextField(default=u''),
    'smtp_use_tls':             DBooleanField(default=False),
    'email_signature':          DTextField(default=__summary__),
    'log_email_only':           DBooleanField(default=False),

    'gravatar/url':             DTextField(
        default=u'http://www.gravatar.com/avatar/',
        help_text=l_(u'the URL for gravatars.  Usually it does not really make '
                     u'sense to change this value.')),
    'gravatar/fallback':        DChoiceField(choices=[
            ('default', 'Default'),
            ('identicon', 'IdentIcon'),
            ('monsterid', 'MonsterId'),
            ('wavatar', 'wAvatar'),
            ('404', l_(u'No default images.'))
        ], default="404", help_text=l_(u'the gravatar fallback to use')),

    'gravatar/rating':        DChoiceField(choices=[('g', u'G'),
                                                    ('pg', u'PG'),
                                                    ('r', u'R'),
                                                    ('X', u'X - Explicit')
        ], default="g", help_text=l_(u' the gravatar rating allowed')),

    'passthrough_errors':       DBooleanField(default=False,
        help_text=l_(u'If this is set to true, errors in ILog '
        u'are not caught so that debuggers can catch it instead.  This is '
        u'useful for development.')),

    'force_https':              DBooleanField(default=False, help_text=l_(
        u'If a request to an http URL comes in, ILog will redirect to the same '
        u'URL on https if this is safely possible.  This requires a working '
        u'SSL setup, otherwise ILOG will become unresponsive.')),
    'maintenance_mode':         DBooleanField(default=False, help_text=l_(
        u'If set to true, ILog enables the maintenance mode.')),

}

HIDDEN_KEYS = ('secret_key',)

#: header for the config file
CONFIG_HEADER = '''\
# ILog configuration file
# This file is also updated by the ILog admin interface.
# The charset of this file must be utf-8!

'''

del l_
