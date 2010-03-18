# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.exceptions import NotFound

from ilog.i18n import _
from ilog.database import db, Group
from ilog.forms import DeleteGroupForm, EditGroupForm
from ilog.privileges import require_privilege, ILOG_ADMIN
from ilog.utils import flash
from ilog.utils.http import redirect_to
from ilog.views.admin.manage import render_manage_view

def render_groups_view(template_name, *args, **kwargs):
    return render_manage_view(template_name, _active_submenu='groups',
                              *args, **kwargs)


@require_privilege(ILOG_ADMIN)
def list(request):
    groups = Group.query.all()
    return render_groups_view('list.html', groups=groups)


@require_privilege(ILOG_ADMIN)
def edit(request, group_id=None):
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
    return render_groups_view('edit.html', form=form.as_widget())


@require_privilege(ILOG_ADMIN)
def delete(request, group_id=None):
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

    return render_groups_view('delete.html', form=form.as_widget())

