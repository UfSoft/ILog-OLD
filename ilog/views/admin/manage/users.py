# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.exceptions import NotFound

from ilog.i18n import _
from ilog.database import db, User
from ilog.forms import DeleteUserForm, EditUserForm
from ilog.privileges import require_privilege, ILOG_ADMIN
from ilog.utils import flash
from ilog.utils.http import redirect_to
from ilog.views.admin.manage import render_manage_view

def render_accounts_view(template_name, *args, **kwargs):
    return render_manage_view(template_name, _active_submenu='users',
                              *args, **kwargs)


@require_privilege(ILOG_ADMIN)
def list(request):
    users = User.query.all()
    return render_accounts_view('list.html', users=users)


@require_privilege(ILOG_ADMIN)
def edit(request, user_id=None):
    user = None
    if user_id is not None:
        user = User.query.get(user_id)
        if user is None:
            raise NotFound()
    form = EditUserForm(user)
    if request.method == 'POST':
        if request.form.get('cancel'):
            return form.redirect('admin.manage.users')
        elif request.form.get('delete') and user:
            return redirect_to('admin.manage.users.delete',
                               user_id=user.uuid)
        elif form.validate(request.form):
            if user is None:
                user = form.make_user()
                msg = _(u'User “%s” created successfully.')
                icon = 'add'
            else:
                form.save_changes()
                msg = _(u'User “%s” edited successfully.')
                icon = 'info'
            db.session.commit()
            flash(msg % user.username, icon)

            if request.form.get('save'):
                return form.redirect('admin.manage.users')
            return redirect_to('admin.manage.users.edit', user_id=user.uuid)
    return render_accounts_view('edit.html', form=form.as_widget())


@require_privilege(ILOG_ADMIN)
def delete(request, user_id=None):
    """Like all other delete screens just that it deletes a user."""
    user = User.query.get(user_id)
    if user is None:
        raise NotFound()
    form = DeleteUserForm(user)


    if request.method == 'POST':
        if request.form.get('cancel'):
            return form.redirect('admin.manage.users.edit',
                                 user_id=user.uuid)
        elif request.form.get('confirm') and form.validate(request.form):
            form.add_invalid_redirect_target('admin.manage.users.edit',
                                             user_id=user.uuid)
            form.delete_group()
            db.commit()
            return form.redirect('admin.manage.users')

    return render_accounts_view('delete.html', form=form.as_widget())

