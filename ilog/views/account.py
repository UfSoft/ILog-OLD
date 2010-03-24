# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import logging
from ilog.application import (get_request, render_response, render_template,
                              url_for, add_navbar_item, add_ctxnavbar_item)
from ilog.database import db, Privilege, Provider, User
from ilog.forms import (AccountProfileForm, DeleteUserForm, LoginForm,
                        RegisterForm)
from ilog.privileges import require_privilege, ENTER_ACCOUNT_PANEL
from ilog.utils import flash
from ilog.utils.http import (get_redirect_target, redirect_back, redirect_to,
                             request_rpx_profile)
from ilog.utils.mail import send_email
from ilog.i18n import _

try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

log = logging.getLogger(__name__)

def render_account_view(template_name, *args, **kwargs):
    template_name = "account/%s" % template_name
    request = get_request()
    if request.user.is_somebody:
        add_navbar_item('account.dashboard', _(u'My Account'))
        add_ctxnavbar_item('account.dashboard', _(u'Dashboard'))
        add_ctxnavbar_item('account.profile', _(u'Profile'))
    return render_response(template_name, *args, **kwargs)


def login(request):
    if request.user.is_somebody:
        flash(_(u"You're already signed in."))
        return redirect_back('index')

    token_url = url_for('account.rpx', _external=True,
                        next=get_redirect_target())

    form = LoginForm()
    if request.method == 'POST' and form.validate(request.form):
        log.debug("Authentication success for %s!",
                  request.form.get('username'))
        flash(_('Welcome back %s!') % request.user.display_name )
        return redirect_back('index')
    return render_account_view('login.html', form=form.as_widget(),
                               token_url=token_url)


def rpx_post(request):
    log.debug("on rpx_post: %s with data: %r", request, request.values)
    if request.method != 'POST':
        return redirect_back('account.login')

    profile = request_rpx_profile(request)

    if profile:
        # 'identifier' will always be in the payload
        # this is the unique identifier that you use to sign the user
        # in to your site
        identifier = profile['identifier']

        provider = Provider.query.get(identifier)
        if not provider:
            request.session['rpx_profile'] = profile
            flash("Welcome to ILog please confirm your details and "
                  "create your account!")
            return redirect_to('account.register')

        log.debug("Logging in user: %s", provider.account.username)
        request.login(provider.account.id)
        flash(_('Welcome back %s!') % provider.account.display_name )

        if not provider.account.active:
            flash(_(u"Your account is not active either because you just "
                    u"registered and have not yet verified your email address "
                    u"or because you've made changes that require you to re-"
                    u"activate your account. Your privileges are narrow."))


        if 'next' in request.args:
            return redirect_back('index')
        return redirect_to('index')
    return redirect_to('account.login')


def logout(request):
    if request.user.is_somebody:
        request.logout()
        flash(_(u"You've been successfully logged out."))
    return redirect_to('index')


@require_privilege(ENTER_ACCOUNT_PANEL)
def profile(request):
    form = AccountProfileForm(request.user)

    if request.method=='POST' and form.validate(request.form):
        reactication_required = False
        account = request.user

        if 'delete' in request.form:
            return form.redirect('account.delete')

        posted_email = request.form.get('email', None)
        if posted_email and (posted_email != account.email):
            reactication_required = True

        form.save_changes()
        db.commit()

        if reactication_required:
            account.set_activation_key()
            db.commit()

            email_contents = render_template(
                'mails/reactivate_account.txt', user=account,
                confirmation_url=url_for('account.activate',
                                         key=account.activation_key,
                                         _external=True))
            send_email(_(u"Re-Activate your account"), email_contents,
                         [account.email], quiet=False)
            flash(_(u"A confirmation email has been sent to \"%s\" to "
                    u"re-activate your account.") % account.email)
        return redirect_back('account.profile')

    token_url = url_for('account.rpx_providers', _external=True,
                        next=get_redirect_target())

    return render_account_view('profile.html', form=form.as_widget(),
                               token_url=token_url)


@require_privilege(ENTER_ACCOUNT_PANEL)
def delete(request):
    form = DeleteUserForm(request.user)
    if request.method == 'POST':
        if request.form.get('cancel'):
            return redirect_back('account.profile')
        elif request.form.get('confirm') and form.validate(request.form):
            form.add_invalid_redirect_target('account.profile')
            form.delete_user()
            db.commit()
            request.logout()
            flash(_(u"Your account was deleted successfully."))
            return form.redirect('index')
    return render_account_view('delete.html', form=form.as_widget())


def register(request):
    if request.user.is_somebody:
        flash(_(u"You have already authenticated."), "error")
        return redirect_back('account.profile')


    rpx_profile = request.session.get('rpx_profile', None)
    if not rpx_profile:
        flash(_(u"Account registrations will be performed after signing-in "
                u"using one of the following services."), "error")
        return redirect_to('account.login')

    display_name = rpx_profile.get('name', None)
    form = RegisterForm({
        'identifier': rpx_profile.get('identifier'),
        'provider': rpx_profile.get('providerName'),
        'username': rpx_profile.get('preferredUsername', ''),
        'display_name': display_name and
                        display_name.get('formatted', '') or '',
        'email': rpx_profile.get('verifiedEmail', rpx_profile.get('email'))
    })

    if request.method == 'POST' and form.validate(request.form):
        provider = Provider.query.get(request.form.get('identifier'))
        if provider:
            flash("We already have an account using this provider", "error")
            return form.redirect('account.login')

        account = User(username=request.form.get('username'),
                       email=request.form.get('email'),
                       display_name=request.form.get('display_name'),
                       passwd=request.form.get('new_password'))
        account.set_activation_key()
        account.providers.add(
            Provider(identifier=request.form.get('identifier'),
                     provider=request.form.get('provider'))
        )
        db.session.add(account)
        db.commit()
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
        request.login(account.id)

        # We've finalised the registration process, remove the rpx profile
        # from the session
        rpx_profile = request.session.pop('rpx_profile', None)
        return redirect_to('index')

    return render_account_view('register.html', form=form.as_widget())

@require_privilege(ENTER_ACCOUNT_PANEL)
def rpx_providers_post(request, token=None):
    if request.method != 'POST':
        return redirect_back('account.profile')

    profile = request_rpx_profile(request)

    if not profile:
        flash(_(u"Something wen't wrong authenticating with this provider"),
              "error")

    if profile:
        # 'identifier' will always be in the payload
        # this is the unique identifier that you use to sign the user
        # in to your site
        identifier = profile['identifier']

        provider = Provider.query.get(identifier)
        if provider:
            if provider in request.user.providers:
                flash(_(u"You already have this login provider associated with "
                        u"your account."), "error")
                return redirect_to('account.profile')
            flash(_(u"Another account(not your's) is already associated with "
                    u"this provider."), "error")
            return redirect_to('account.profile')

        provider = Provider(identifier, profile['providerName'])
        request.user.providers.add(provider)
        db.session.commit()
        flash('Login provider associated successfully!')
    return redirect_to('account.profile')

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
    privilege = Privilege.query.get(ENTER_ACCOUNT_PANEL)
    if not privilege:
        privilege = Privilege(ENTER_ACCOUNT_PANEL)
    account.privileges.add(privilege)
    db.commit()
    flash(_(u"Your account has been successfully activated!"))
    return redirect_back('account.profile')


@require_privilege(ENTER_ACCOUNT_PANEL)
def dashboard(request):
    return render_account_view('dashboard.html')
