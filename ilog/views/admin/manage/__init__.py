
from ilog.application import add_ctxnavbar_item
from ilog.i18n import _
from ilog.views.admin import render_admin_view

def render_manage_view(template_name, _active_submenu='', *args, **kwargs):
    add_ctxnavbar_item('admin.manage.groups', _(u'Groups'))
    add_ctxnavbar_item('admin.manage.users', _(u'Users'))
    add_ctxnavbar_item('admin.manage.networks', _(u'Networks'))
    add_ctxnavbar_item('admin.manage.channels', _(u'Channels'))
    add_ctxnavbar_item('admin.manage.bots', _(u'Bots'))

    _active_menu_item='admin.manage.%s' % _active_submenu
    template_name = 'admin/manage/%s/%s' % (_active_submenu, template_name)

    return render_admin_view(template_name, _active_menu_item=_active_menu_item,
                             *args, **kwargs)