# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import logging

from ilog.application import get_application, get_request
from ilog.database import db, Group, User
from ilog.i18n import _, lazy_gettext, list_languages, list_timezones
from ilog.privileges import bind_privileges
from ilog.utils import forms, validators

log = logging.getLogger(__name__)

class _GroupBoundForm(forms.Form):
    """Internal baseclass for group bound forms."""

    def __init__(self, group, initial=None):
        forms.Form.__init__(self, initial)
        self.app = get_application()
        self.group = group

    def as_widget(self):
        widget = forms.Form.as_widget(self)
        widget.group = self.group
        widget.new = self.group is None
        return widget


class EditGroupForm(_GroupBoundForm):
    """Edit or create a group."""

    groupname = forms.TextField(lazy_gettext(u'Groupname'), max_length=30,
                                validators=[validators.not_empty],
                                required=True)
    privileges = forms.MultiChoiceField(lazy_gettext(u'Privileges'),
                                        widget=forms.CheckboxGroup)

    def __init__(self, group=None, initial=None):
        if group is not None:
            initial = forms.fill_dict(initial,
                groupname=group.name,
                privileges=[x.name for x in group.privileges]
            )
        _GroupBoundForm.__init__(self, group, initial)
        self.privileges.choices = self.app.list_privileges()

    def validate_groupname(self, value):
        query = Group.query.filter_by(name=value)
        if self.group is not None:
            query = query.filter(Group.id != self.group.id)
        if query.first() is not None:
            raise forms.ValidationError(_('This groupname is already in use'))

    def _set_common_attributes(self, group):
        forms.set_fields(group, self.data)
        bind_privileges(group.privileges, self.data['privileges'])

    def make_group(self):
        """A helper function that creates a new group object."""
        group = Group(self.data['groupname'])
        db.session.add(group)
        self._set_common_attributes(group)
        self.group = group
        return group

    def save_changes(self):
        """Apply the changes."""
        self.group.name = self.data['groupname']
        self._set_common_attributes(self.group)


class DeleteGroupForm(_GroupBoundForm):
    """Used to delete a group from the admin panel."""

    what_to_do = forms.ChoiceField(
        lazy_gettext(u'What should ILog do with users assigned to this group?'),
        choices=[
            ('delete_membership', lazy_gettext(u'Do nothing, just detach '
                                               u'the membership')),
            ('relocate', lazy_gettext(u'Move the users to another group'))
        ],
        widget=forms.RadioButtonGroup)

    relocate_to = forms.ModelField(model=Group, key='id',
                                   label=lazy_gettext(u'Relocate users to'),
                                   widget=forms.SelectBox)
#    relocate_to = forms.ChoiceField('foo', choices=[(1, 1), (2, 3)],
#                                    widget=forms.SelectBox)

    def __init__(self, group, initial=None):
        self.relocate_to.choices=[('', u'')] + [
            (g.id, g.name) for g in Group.query.filter(Group.id != group.id)
        ]
        _GroupBoundForm.__init__(self, group,
                                 forms.fill_dict(initial,
                                                 what_to_do='delete_membership'))

    def context_validate(self, data):
        if data['what_to_do'] == 'relocate' and not data['relocate_to']:
            raise forms.ValidationError(_('You have to select a group that '
                                          'gets the users assigned.'))

    def delete_group(self):
        """Deletes a group."""
        if self.data['what_to_do'] == 'relocate':
            new_group = Group.query.get(self.data['relocate_to'].id)
            for user in self.group.users:
                if not new_group in user.groups:
                    user.groups.append(new_group)
        db.commit()
        db.delete(self.group)


class _UserBoundForm(forms.Form):
    """Internal baseclass for user bound forms."""

    def __init__(self, user, initial=None):
        forms.Form.__init__(self, initial)
        self.app = get_application()
        self.user = user

    def as_widget(self):
        widget = forms.Form.as_widget(self)
        widget.user = self.user
        widget.new = self.user is None
        return widget


class LoginForm(forms.Form):
    username     = forms.TextField(_(u"Username"), required=True,
                                   validators=[validators.valid_username])
    password     = forms.TextField(_(u'Password'), required=True,
                                   widget=forms.PasswordInput,
                                   validators=[validators.not_empty])
    remember_me  = forms.BooleanField(_(u'Remember Me'), widget=forms.Checkbox)

    def context_validate(self, data):
        public_data = data.copy()
        public_data['password'] = '*****'
        log.debug("Validating context with data: %s", public_data)
        account = User.query.filter(User.username==data['username']).first()
        if not account.check_password(data['password']):
            log.debug("Failed authentication for %s", data['username'])
            raise forms.ValidationError(_(u"Failed login!"))
        get_request().login(account.id, permanent=data['remember_me'])


class RegisterForm(forms.Form):

    identifier   = forms.TextField(required=True, widget=forms.HiddenInput)
    provider     = forms.TextField(_(u"Provider"), required=True,
                                   widget=forms.HiddenInput)
    display_name = forms.TextField(_(u"Display Name"), required=True)
    username     = forms.TextField(_(u"Desired Username"), required=True,
                                   validators=[validators.unique_username])
    email        = forms.TextField(_(u"Email Address"), required=True,
                                   validators=[validators.unique_email])
    new_password = forms.TextField(_(u'New password'), required=True,
                                   widget=forms.PasswordInput,
                                   validators=[validators.not_empty])
    rep_password = forms.TextField(_(u'Repeat password'), required=True,
                                   widget=forms.PasswordInput,
                                   validators=[validators.not_empty])

    def context_validate(self, data):
        if data['new_password'] != data['rep_password']:
            raise forms.ValidationError(_('The two passwords don\'t match.'))


class AccountProfileForm(_UserBoundForm):
    id           = forms.TextField(required=True, widget=forms.HiddenInput)
    username     = forms.TextField(_(u"Username"), required=True)
    display_name = forms.TextField(_(u"Display Name"), required=True)
    email        = forms.TextField("Email Address", required=True,
                                   validators=[validators.not_empty,
                                               validators.is_valid_email])
    password     = forms.TextField(u'New password',
                                   widget=forms.PasswordInput)
    rep_password = forms.TextField(u'Repeat password',
                                   widget=forms.PasswordInput)
    locale       = forms.ChoiceField(_(u'Language'))
    tzinfo       = forms.ChoiceField(_(u'Timezone'))

    def __init__(self, user=None, initial=None):
        if user is not None:
            initial = forms.fill_dict(initial,
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                email=user.email,
                privileges=[x.name for x in user.privileges],
                groups=[g.name for g in user.groups],
                locale=user.locale,
                tzinfo=user.tzinfo
            )
        _UserBoundForm.__init__(self, user, initial)
        self.locale.choices = list_languages()
        self.tzinfo.choices = list_timezones()

    def validate_email(self, email):
        if self.user and (email != self.user.email):
            validators.unique_email(self, email)

    def context_validate(self, data):
        if data['password'] and (data['password'] != data['rep_password']):
            raise forms.ValidationError(_('The two passwords don\'t match.'))

    def _set_common_attributes(self, user):
        forms.set_fields(user, self.data, 'display_name', 'email', 'locale', 'tzinfo')

    def save_changes(self):
        """Apply the changes."""
        self._set_common_attributes(self.user)


class EditUserForm(AccountProfileForm):
    """Edit or create a user."""

    privileges = forms.MultiChoiceField(lazy_gettext(u'Privileges'),
                                        widget=forms.CheckboxGroup)
    groups = forms.MultiChoiceField(lazy_gettext(u'Groups'),
                                    widget=forms.CheckboxGroup)

    def __init__(self, user=None, initial=None):
        if user is not None:
            initial = forms.fill_dict(initial,
                privileges=[x.name for x in user.privileges],
                groups=[g.name for g in user.groups],
            )
        AccountProfileForm.__init__(self, user, initial)
        self.privileges.choices = self.app.list_privileges()
        self.groups.choices = [g.name for g in Group.query.all()]

        self.username.editable = True
        self.username.required = self.password.required = user is None

    def validate_username(self, username):
        query = User.query.filter_by(username=username)
        if self.user is not None:
            query = query.filter(User.id != self.user.id)
        if query.first() is not None:
            raise forms.ValidationError(_('This username is already in use'))

    def _set_common_attributes(self, user):
        bind_privileges(user.privileges, self.data['privileges'], user)
        bound_groups = set(g.name for g in user.groups)
        choosen_groups = set(self.data['groups'])
        group_mapping = dict((g.name, g) for g in Group.query.all())
        # delete groups
        for group in (bound_groups - choosen_groups):
            user.groups.remove(group_mapping[group])
        # and add new groups
        for group in (choosen_groups - bound_groups):
            user.groups.append(group_mapping[group])

    def make_user(self):
        """A helper function that creates a new user object."""
        user = User(username=self.data['username'],
                    email=self.data['email'],
                    password=self.data['password'])
        self._set_common_attributes(user)
        self.user = user
        return user

    def save_changes(self):
        """Apply the changes."""
        if self.username.editable:
            self.user.username = self.data['username']
        if self.data['password']:
            self.user.set_password(self.data['password'])
        self.user.email = self.data['email']
        self._set_common_attributes(self.user)


class DeleteUserForm(_UserBoundForm):
    """Used to delete a user from the admin panel."""

    def __init__(self, user, initial=None):
        _UserBoundForm.__init__(self, user, initial)

    def delete_user(self):
        """Deletes the user."""
        # XXX: find all the identities by this account and delete them too
        db.delete(self.user)
