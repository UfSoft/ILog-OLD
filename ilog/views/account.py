# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import urllib
import urllib2
import logging
import simplejson
from ilog.application import (get_request, render_response, render_template,
                              url_for, add_navbar_item, add_ctxnavbar_item)
from ilog.database import User, session
from ilog.privileges import ENTER_ACCOUNT_PANEL
from ilog.utils import flash
from ilog.utils.http import get_redirect_target, redirect_back, redirect_to
from ilog.utils.mail import send_email
from ilog.i18n import _, list_languages, list_timezones
from ilog.utils import forms
from ilog.utils.validators import (unique_email, unique_username,
                                   valid_username, is_valid_email, not_empty)

try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

log = logging.getLogger(__name__)

def render_account_view(*args, **kwargs):
    request = get_request()
    if request.user.is_somebody:
        add_navbar_item('account.dashboard', _(u'My Account'))
        add_ctxnavbar_item('account.dashboard', _(u'Dashboard'))
        add_ctxnavbar_item('account.profile', _(u'Profile'))
    return render_response(*args, **kwargs)


class LoginForm(forms.Form):
    username     = forms.TextField(_(u"Username"), required=True,
                                   validators=[valid_username])
    password     = forms.TextField(_(u'Password'), required=True,
                                   widget=forms.PasswordInput,
                                   validators=[not_empty])
    remember_me  = forms.BooleanField(_(u'Remember Me'), widget=forms.Checkbox)

    def context_validate(self, data):
        log.debug("Validating context with data: %s", data)
        account = User.query.filter(User.username==data['username']).first()
        if not account.check_password(data['password']):
            log.debug("Failed authentication for %s", data['username'])
            raise forms.ValidationError(_(u"Failed login!"))
        get_request().login(account.uuid, permanent=data['remember_me'])


def login(request):
    if request.user.is_somebody:
        flash(_(u"You're already signed in."))
        return redirect_back('index')

    token_url = url_for('account.rpx', _external=True,
                        next=get_redirect_target())

    form = LoginForm()
    if request.method == 'POST' and form.validate(request.form):
        log.debug("Authentication success for %s!", request.values['username'])
        return redirect_back('index')
    return render_account_view('account/login.html', form=form.as_widget(),
                       token_url=token_url)

def rpx_post(request, token=None):
    log.debug("on rpx_post: %s with data: %r", request, request.values)
    if request.method != 'POST':
        return redirect_back('account.login')

    token = request.values.get('token')
    params = urllib.urlencode({
        'token': token,
        'apiKey': request.app.cfg['rpxnow/api_key'],
#        'format': 'json'
    })
    http_response = urllib2.urlopen('https://rpxnow.com/api/v2/auth_info',
                                    params)
    auth_info = simplejson.loads(http_response.read())

    del http_response

    if auth_info['stat'] == 'ok':
        profile = auth_info['profile']

        # 'identifier' will always be in the payload
        # this is the unique idenfifier that you use to sign the user
        # in to your site
        identifier = profile['identifier']

        account = User.query.filter(User.identifier==identifier).first()
        if not account:
            request.session['rpx_profile'] = profile
            flash("Welcome to ILog please confirm your details and "
                  "create your account!")
            return redirect_to('account.register')

        log.debug("Logging in user: %s", account.username)
        request.login(account.uuid)
        flash('Logged In!')
#        if not account.agreed_to_tos:
#            self.flash("You have not yet agreed to our Terms and Conditions",
#                       "error")
        if not account.active:
            flash(_(u"Your have not active either because you just registered "
                    u"or because you've made changes that require you to re-"
                    u"activate your account. Your privileges are narrow"))


        if 'next' in request.args:
            return redirect_back('index')
        return redirect_to('index')
    return redirect_to('account.login')


def logout(request):
    request.logout()
    flash(_(u"You've been successfully logged out."))
    return redirect_to('index')


class AccountProfileForm(forms.Form):
    uuid         = forms.TextField(required=True, widget=forms.HiddenInput)
    display_name = forms.TextField(_(u"Display Name"), required=True)
    email        = forms.TextField("Email Address", required=True,
                                   validators=[not_empty, is_valid_email])
    password     = forms.TextField(u'New password',
                                   widget=forms.PasswordInput)
    rep_password = forms.TextField(u'Repeat password',
                                   widget=forms.PasswordInput)
    locale       = forms.ChoiceField(_(u'Language'), choices=list_languages())
    tzinfo       = forms.ChoiceField(_(u'Timezone'), choices=list_timezones())

    def __init__(self, *args, **kwargs):
        account = get_request().user
        kwargs['initial'] = dict(uuid = account.uuid,
                                 display_name = account.display_name,
                                 email = account.email,
                                 locale = account.locale,
                                 tzinfo = account.tzinfo)
        forms.Form.__init__(self, *args, **kwargs)
        self.account = account

    def validate_email(self, email):
        if email != self.account.email:
            unique_email(self, email)

    def context_validate(self, data):
        if data['password'] and (data['password'] != data['rep_password']):
            raise forms.ValidationError(_('The two passwords don\'t match.'))


def profile(request):
    form = AccountProfileForm()

    if request.method=='POST' and form.validate(request.form):
        reactication_required = False
        account = request.user

        for key, value in request.form.iteritems():
            if hasattr(account, key):
                setattr(account, key, value)
                if (key == 'email') and (account.email != value):
                    reactication_required = True

        if reactication_required:
            account.set_activation_key()
            session.commit()

            email_contents = render_template(
                'mails/reactivate_account.txt', user=account,
                confirmation_url=url_for('account.activate',
                                         key=account.activation_key,
                                         _external=True))
            send_email(_(u"Re-Activate your account"), email_contents,
                         [account.email], quiet=False)
            flash(_(u"A confirmation email has been sent to \"%s\" to "
                    u"re-activate your account.") % account.email )
    return render_account_view('account/register.html', form=form.as_widget())


class RegisterForm(forms.Form):

    identifier   = forms.TextField(required=True, widget=forms.HiddenInput)
    display_name = forms.TextField(_(u"Display Name"), required=True)
    username     = forms.TextField(_(u"Desired Username"), required=True,
                                   validators=[unique_username])
    email        = forms.TextField(_(u"Email Address"), required=True,
                                   validators=[unique_email])
    new_password = forms.TextField(_(u'New password'), required=True,
                                   widget=forms.PasswordInput,
                                   validators=[not_empty])
    rep_password = forms.TextField(_(u'Repeat password'), required=True,
                                   widget=forms.PasswordInput,
                                   validators=[not_empty])

    def context_validate(self, data):
        if data['new_password'] != data['rep_password']:
            raise forms.ValidationError(_('The two passwords don\'t match.'))

def register(request):
    if request.user.is_somebody:
        flash(_(u"You have already authenticated."), "error")
        return redirect_back('account.profile')

    elif request.method == 'POST':
        form = RegisterForm(request.form)
        if form.validate(request.form):
            account = User(
                identifier=request.form.get('identifier', None),
                provider=request.form.get('providerName', '').lower(),
                username=request.form.get('username', None),
                email=request.form.get('email', None),
                display_name=request.form.get('display_name', None),
                passwd=request.form.get('new_password', None),
            )
            account.set_activation_key()
            session.add(account)
            session.commit()
            email_contents = render_template(
                'mails/activate_account.txt',
                user=account.display_name,
                confirmation_url=url_for('account.activate',
                                         key=account.activation_key,
                                         _external=True))
            send_email(_(u"Activate your account"), email_contents,
                         [account.email], quiet=False)
            flash(_(u"A confirmation email has been sent to \"%s\" to activate "
                    u"your account.") % account.email )
            request.login(account.uuid, permanent=True)
            return redirect_to('index')
        else:
            return render_account_view('account/register.html', form=form.as_widget())

    rpx_profile = request.session.pop('rpx_profile', None)
    if not rpx_profile:
        flash(_(u"Account registrations will be performed after signing-in "
                u"using one of the following servives."), "error")
        return redirect_to('account.login')

    display_name = rpx_profile.get('name', None)
    form = RegisterForm({
        'identifier': rpx_profile.get('identifier'),
        'username': rpx_profile.get('preferredUsername', ''),
        'display_name': display_name and
                        display_name.get('formatted', '') or '',
        'email': rpx_profile.get('verifiedEmail', rpx_profile.get('email'))
    })

    return render_account_view('account/register.html', form=form.as_widget())

def activate_account(request, key):
    # Delete too old activations
    old_registrations = User.query.too_old_activations().delete()
    log.debug("Deleted %d old expired account registrations",
              old_registrations)
    account = User.query.filter(User.activation_key==key).first()
    if not account:
        flash("No account could be activated. Maybe it was too old.", "error")
        return redirect_back('index')
    account.activate()
    account.privileges.add(ENTER_ACCOUNT_PANEL)
    session.commit()
    flash(_(u"Your account has been successfully activated!"))
    return redirect_back('account.profile')

def dashboard(request):
    return render_account_view('account/dashboard.html')
