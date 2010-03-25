# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from copy import copy

from ilog.application import add_ctxnavbar_item, get_application
from ilog.utils import forms
from ilog.views.admin import render_admin_view
from ilog.i18n import _
from ilog.utils import flash
from ilog.utils.http import redirect_to
from ilog.utils.forms import Field, _next_position_hint, DEFAULT_VARS

def render_options_view(template_name, *args, **kwargs):
    add_ctxnavbar_item('admin.options.basic', _(u'Basic'))
    add_ctxnavbar_item('admin.options.advanced', _(u'Advanced'))
    add_ctxnavbar_item('admin.options.rpxnow', _(u'RPXNow.com'))
    add_ctxnavbar_item('admin.options.gravatar', _(u'Gravatar'))
    add_ctxnavbar_item('admin.options.email', _(u'E-Mail'))
    add_ctxnavbar_item('admin.options.cache', _(u'Cache'))
    template_name = 'admin/options/%s' % template_name
    return render_admin_view(template_name, *args, **kwargs)



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

class _ConfigForm(forms.Form):

    def __init__(self, initial=None, parent=None):
        self.app = get_application()
        self.parent = parent
        if initial is None:
            initial = {}
            for name in self.fields:
                if parent:
                    initial[name] = self.app.cfg["%s/%s" % (parent, name)]
                else:
                    initial[name] = self.app.cfg[name]
        forms.Form.__init__(self, initial)

    def _apply(self, t, skip):
        for key, value in self.data.iteritems():
            if self.parent:
                key = "%s/%s" % (self.parent, key)
            if key not in skip:
                t[key] = value

    def apply(self):
        t = self.app.cfg.edit()
        self._apply(t, set())
        t.commit()


class BasicOptionsForm(_ConfigForm):

    ilog_url        = config_field('ilog_url', label=_(u'ILog Base URL'))
    ilog_email      = config_field('ilog_email', label=_(u'ILog E-Mail'))
    language        = config_field('language', label=_(u'Language'))
    timezone        = config_field('timezone', label=_(u'Timezone'))
    cookie_name     = config_field('cookie_name', label=_(u'Cookie Name'))


class AdvancedOptionsForm(_ConfigForm):
    database_uri        = config_field('database_uri', label=_(u'Database URI'))
    database_debug      = config_field('database_debug',
                                       label=_(u'Database Debug'))
    secret_key          = config_field('secret_key', label=_(u'Secret Key'))
    force_https         = config_field('force_https', label=_(u'Force HTTPS'))
    maintenance_mode    = config_field('maintenance_mode',
                                       label=_(u'Maintenance Mode'))
    passthrough_errors  = config_field('passthrough_errors',
                                       label=_(u'Passtrough Errors'))


class CacheOptionsForm(_ConfigForm):
    cache_system            = config_field('cache_system',
                                           label=_(u'Cache System'))
    cache_timeout           = config_field('cache_timeout',
                                           label=_(u'Cache Timeout'))
    enable_eager_caching    = config_field('enable_eager_caching',
                                           label=_(u'Eager Caching'))
    memcached_servers       = config_field('memcached_servers',
                                           label=_(u'Memcached Servers'))
    filesystem_cache_path   = config_field('filesystem_cache_path',
                                           label=_(u'Filesystem Cache Path'))


class EmailOptionsForm(_ConfigForm):
    smtp_host       = config_field('smtp_host', label=_(u'Host'))
    smtp_port       = config_field('smtp_port', label=_(u'Port'))
    smtp_user       = config_field('smtp_user', label=_(u'User'))
    smtp_password   = config_field('smtp_password', label=_(u'Password'),
                                   widget=forms.PasswordInput)
    smtp_from_name  = config_field('smtp_port', label=_(u'From Name'))
    smtp_use_tls    = config_field('smtp_use_tls', label=_(u'Use TLS'))
    log_email_only  = config_field('log_email_only', label=_(u'Log Email Only'))
    email_signature = config_field('email_signature',
                                   label=_(u'Email Signature'),
                                   widget=forms.Textarea)


class GravatarOptionsForm(_ConfigForm):
    url         = config_field('gravatar/url', label=_(u'URL'))
    fallback    = config_field('gravatar/fallback', label=_(u'Fallback'))
    rating      = config_field('gravatar/rating', label=_(u'Rating'))

    def __init__(self, initial=None):
        _ConfigForm.__init__(self, initial, parent='gravatar')


class RPXNowOptionsForm(_ConfigForm):
    app_domain  = config_field('rpxnow/app_domain',
                               label=_(u'Application Domain'))
    api_key     = config_field('rpxnow/api_key', label=_(u'API Key'))

    def __init__(self, initial=None):
        _ConfigForm.__init__(self, initial, parent='rpxnow')


def basic_options(request):
    # flash an altered message if the url is ?altered=true. For more information
    # see the comment that redirects to the url below.
    if request.args.get('altered') == 'true':
        flash(_(u'Configuration altered successfully.'), 'configure')
        return redirect_to('admin.options.basic')

    form = BasicOptionsForm()
    if request.method == 'POST' and form.validate(request.form):
        form.apply()
        # because the configuration page could change the language and
        # we want to flash the message "configuration changed" in the
        # new language rather than the old. As a matter of fact we have
        # to wait for Zine to reload first which is why we do the
        # actual flashing after one reload.
        return redirect_to('admin.options.basic', altered='true')
    return render_options_view('basic.html', form=form.as_widget())

def advanced_options(request):
    form = AdvancedOptionsForm()
    if request.method == 'POST' and form.validate(request.form):
        form.apply()
        flash(_(u'Configuration altered successfully.'), 'configure')
        return redirect_to('admin.options.advanced')
    return render_options_view('advanced.html', form=form.as_widget())

def rpxnow_options(request):
    form = RPXNowOptionsForm()
    if request.method == 'POST' and form.validate(request.form):
        form.apply()
        flash(_(u'Configuration altered successfully.'), 'configure')
        return redirect_to('admin.options.rpxnow')
    return render_options_view('rpxnow.html', form=form.as_widget())

def gravatar_options(request):
    form = GravatarOptionsForm()
    if request.method == 'POST' and form.validate(request.form):
        form.apply()
        flash(_(u'Configuration altered successfully.'), 'configure')
        return redirect_to('admin.options.gravatar')
    return render_options_view('gravatar.html', form=form.as_widget())

def email_options(request):
    form = EmailOptionsForm()
    if request.method == 'POST' and form.validate(request.form):
        form.apply()
        flash(_(u'Configuration altered successfully.'), 'configure')
        return redirect_to('admin.options.email')
    return render_options_view('email.html', form=form.as_widget())

def cache_options(request):
    form = CacheOptionsForm()
    if request.method == 'POST' and form.validate(request.form):
        form.apply()
        flash(_(u'Configuration altered successfully.'), 'configure')
        return redirect_to('admin.options.cache')
    return render_options_view('cache.html', form=form.as_widget())
