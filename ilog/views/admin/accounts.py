# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.exceptions import NotFound

from ilog.application import add_ctxnavbar_item
from ilog.i18n import _
from ilog.database import db, Group, User
from ilog.forms import (DeleteGroupForm, EditGroupForm,
#                        DeleteUserForm, EditUserForm
                        )
from ilog.privileges import require_privilege, ILOG_ADMIN
from ilog.utils import flash, forms, validators
from ilog.utils.http import redirect_to
from ilog.views.admin import render_admin_view

def render_accounts_view(template_name, *args, **kwargs):
#    add_ctxnavbar_item('admin.manage.index', _(u'Overview'))
    add_ctxnavbar_item('admin.manage.groups', _(u'Groups'))
    add_ctxnavbar_item('admin.manage.users', _(u'Users'))

    template_name = 'admin/accounts/%s' % template_name
    return render_admin_view(template_name, *args, **kwargs)


@require_privilege(ILOG_ADMIN)
def groups(request):
    groups = Group.query.all()
    return render_accounts_view('groups.html', groups=groups)


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
            return form.redirect('admin.manage.groups')
        elif request.form.get('delete') and group:
            return redirect_to('admin.manage.groups.delete',
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
                return form.redirect('admin.manage.groups')
            return redirect_to('admin.manage.groups.edit', group_id=group.id)
    return render_accounts_view('groups_edit.html', form=form.as_widget(),
                                _active_menu_item='admin.manage.groups')


@require_privilege(ILOG_ADMIN)
def groups_delete(request, group_id=None):
    """Like all other delete screens just that it deletes a group."""
    group = Group.query.get(group_id)
    if group is None:
        raise NotFound()
    form = DeleteGroupForm(group)


    if request.method == 'POST':
        if request.form.get('cancel'):
            return form.redirect('admin.manage.groups.edit',
                                 group_id=group.id)
        elif request.form.get('confirm') and form.validate(request.form):
            form.add_invalid_redirect_target('admin.manage.groups.edit',
                                             group_id=group.id)
            form.delete_group()
            db.commit()
            return form.redirect('admin.manage.groups')

    return render_accounts_view('groups_delete.html',
                               _active_menu_item='admin.manage.groups',
                               form=form.as_widget())
