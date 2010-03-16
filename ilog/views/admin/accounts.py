# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.exceptions import NotFound

from ilog.application import (add_ctxnavbar_item, get_request, get_application,
                              render_response)
from ilog.i18n import _, lazy_gettext
from ilog.database import db, Group, User
from ilog.privileges import bind_privileges, require_privilege, ILOG_ADMIN
from ilog.utils import flash, forms, validators
from ilog.utils.http import redirect_to
from ilog.views.admin import render_admin_view

def render_accounts_view(template_name, *args, **kwargs):
#    add_ctxnavbar_item('admin.accounts.index', _(u'Overview'))
    add_ctxnavbar_item('admin.accounts.groups', _(u'Groups'))
    add_ctxnavbar_item('admin.accounts.users', _(u'Users'))

    template_name = 'admin/accounts/%s' % template_name
    return render_admin_view(template_name, *args, **kwargs)


@require_privilege(ILOG_ADMIN)
def groups(request):
    groups = Group.query.all()
    return render_accounts_view('groups.html', groups=groups)


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


@require_privilege(ILOG_ADMIN)
def groups_edit(request, group_id=None):
    group = None
    if group_id is not None:
        group = Group.query.get(group_id)
        if group is None:
            raise NotFound()
    form = EditGroupForm(group)
    if request.method == 'POST':
        if request.form.get('cancel'):
            return form.redirect('admin.accounts.groups')
        elif request.form.get('delete') and group:
            return redirect_to('admin.accounts.groups.delete',
                               group_id=group.id)
        elif form.validate(request.form):
            if group is None:
                group = form.make_group()
                msg = _(u'Group “%s” created successfully.')
                icon = 'add'
            else:
                form.save_changes()
                msg = _(u'Group “%s” edited successfully.')
                icon = 'info'
            db.session.commit()
            flash(msg % group.name, icon)

            if request.form.get('save'):
                return form.redirect('admin.accounts.groups')
            return redirect_to('admin.accounts.groups.edit', group_id=group.id)
    return render_accounts_view('groups_edit.html', form=form.as_widget(),
                                _active_menu_item='admin.accounts.groups')


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

@require_privilege(ILOG_ADMIN)
def groups_delete(request, group_id=None):
    """Like all other delete screens just that it deletes a group."""
    group = Group.query.get(group_id)
    if group is None:
        raise NotFound()
    form = DeleteGroupForm(group)


    if request.method == 'POST':
        if request.form.get('cancel'):
            return form.redirect('admin.accounts.groups.edit',
                                 group_id=group.id)
        elif request.form.get('confirm') and form.validate(request.form):
            form.add_invalid_redirect_target('admin.accounts.groups.edit',
                                             group_id=group.id)
            form.delete_group()
            db.commit()
            return form.redirect('admin.accounts.groups')

    return render_accounts_view('groups_delete.html',
                               _active_menu_item='admin.accounts.groups',
                               form=form.as_widget())

