# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================


from ilog.application import get_application
from ilog.database import db, Group, User
from ilog.i18n import _, lazy_gettext
from ilog.privileges import bind_privileges
from ilog.utils import forms, validators

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


#class _UserBoundForm(forms.Form):
#    """Internal baseclass for user bound forms."""
#
#    def __init__(self, user, initial=None):
#        forms.Form.__init__(self, initial)
#        self.app = get_application()
#        self.user = user
#
#    def as_widget(self):
#        widget = forms.Form.as_widget(self)
#        widget.user = self.user
#        widget.new = self.user is None
#        return widget
#
#
#class EditUserForm(_UserBoundForm):
#    """Edit or create a user."""
#
#    username = forms.TextField(lazy_gettext(u'Username'), max_length=30,
#                               validators=[validators.not_empty],
#                               required=True)
#    real_name = forms.TextField(lazy_gettext(u'Realname'), max_length=180)
#    display_name = forms.ChoiceField(lazy_gettext(u'Display name'))
#    description = forms.TextField(lazy_gettext(u'Description'),
#                                  max_length=5000, widget=forms.Textarea)
#    email = forms.TextField(lazy_gettext(u'Email'), required=True,
#                            validators=[is_valid_email()])
#    www = forms.TextField(lazy_gettext(u'Website'),
#                          validators=[is_valid_url()])
#    password = forms.TextField(lazy_gettext(u'Password'),
#                               widget=forms.PasswordInput)
#    privileges = forms.MultiChoiceField(lazy_gettext(u'Privileges'),
#                                        widget=forms.CheckboxGroup)
#    groups = forms.MultiChoiceField(lazy_gettext(u'Groups'),
#                                    widget=forms.CheckboxGroup)
#
#    def __init__(self, user=None, initial=None):
#        if user is not None:
#            initial = forms.fill_dict(initial,
#                username=user.username,
#                real_name=user.real_name,
#                display_name=user._display_name,
#                description=user.description,
#                email=user.email,
#                www=user.www,
#                privileges=[x.name for x in user.own_privileges],
#                groups=[g.name for g in user.groups],
#                is_author=user.is_author
#            )
#        _UserBoundForm.__init__(self, user, initial)
#        self.display_name.choices = [
#            (u'$username', user and user.username or _('Username')),
#            (u'$real_name', user and user.real_name or _('Realname'))
#        ]
#        self.privileges.choices = self.app.list_privileges()
#        self.groups.choices = [g.name for g in Group.query.all()]
#        self.password.required = user is None
#
#    def validate_username(self, value):
#        query = User.query.filter_by(username=value)
#        if self.user is not None:
#            query = query.filter(User.id != self.user.id)
#        if query.first() is not None:
#            raise ValidationError(_('This username is already in use'))
#
#    def _set_common_attributes(self, user):
#        forms.set_fields(user, self.data, 'www', 'real_name', 'description',
#                         'display_name', 'is_author')
#        bind_privileges(user.own_privileges, self.data['privileges'], user)
#        bound_groups = set(g.name for g in user.groups)
#        choosen_groups = set(self.data['groups'])
#        group_mapping = dict((g.name, g) for g in Group.query.all())
#        # delete groups
#        for group in (bound_groups - choosen_groups):
#            user.groups.remove(group_mapping[group])
#        # and add new groups
#        for group in (choosen_groups - bound_groups):
#            user.groups.append(group_mapping[group])
#
#    def make_user(self):
#        """A helper function that creates a new user object."""
#        user = User(self.data['username'], self.data['password'],
#                    self.data['email'])
#        self._set_common_attributes(user)
#        self.user = user
#        return user
#
#    def save_changes(self):
#        """Apply the changes."""
#        self.user.username = self.data['username']
#        if self.data['password']:
#            self.user.set_password(self.data['password'])
#        self.user.email = self.data['email']
#        self._set_common_attributes(self.user)
#
#
#class DeleteUserForm(_UserBoundForm):
#    """Used to delete a user from the admin panel."""
#
#    action = forms.ChoiceField(lazy_gettext(u'What should Zine do with posts '
#                                            u'written by this user?'), choices=[
#        ('delete', lazy_gettext(u'Delete them permanently')),
#        ('reassign', lazy_gettext(u'Reassign posts'))
#    ], widget=forms.RadioButtonGroup)
#    reassign_to = forms.ModelField(User, 'id',
#                                   lazy_gettext(u'Reassign posts to'),
#                                   widget=forms.SelectBox)
#
#    def __init__(self, user, initial=None):
#        self.reassign_to.choices = [('', u'')] + [
#            (u.id, u.username)
#            for u in User.query.filter(User.id != user.id)
#        ]
#        _UserBoundForm.__init__(self, user, forms.fill_dict(initial,
#            action='reassign'
#        ))
#
#    def context_validate(self, data):
#        if data['action'] == 'reassign' and not data['reassign_to']:
#            raise ValidationError(_('You have to select a user to reassign '
#                                    'the posts to.'))
#
#    def delete_user(self):
#        """Deletes the user."""
#        if self.data['action'] == 'reassign':
#            db.execute(posts.update(posts.c.author_id == self.user.id), dict(
#                author_id=self.data['reassign_to'].id
#            ))
#
#        # XXX: find all the identities by this account and delete them too
#
#        db.delete(self.user)
