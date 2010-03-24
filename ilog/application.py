# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import logging
from inspect import getdoc
from os import environ, path
from time import time
from urlparse import urlparse

from babel.core import Locale
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from werkzeug.contrib.securecookie import SecureCookie
from werkzeug.exceptions import HTTPException, Forbidden, NotFound
from werkzeug.urls import url_quote, url_encode
from werkzeug.utils import redirect as _redirect
from werkzeug.wrappers import Request as RequestBase, Response as ResponseBase
from werkzeug.wsgi import ClosingIterator, SharedDataMiddleware

from ilog import _core, i18n
from ilog.cache import get_cache
from ilog.environment import SHARED_DATA, TEMPLATE_PATH
from ilog.utils import flash, htmlhelpers, local, local_manager
from ilog.utils.exceptions import UserException

log = logging.getLogger(__name__)

class InternalError(UserException):
    """Subclasses of this exception are used to signal internal errors that
    should not happen, but may do if the configuration is garbage.  If an
    internal error is raised during request handling they are converted into
    normal server errors for anonymous users (but not logged!!!), but if the
    current user is an administrator, the error is displayed.
    """

    help_text = None

def get_request():
    """Return the current request.  If no request is available this function
    returns `None`.
    """
    return getattr(local, 'request', None)


def get_application():
    """Get the application instance.  If the application was not yet set up
    the return value is `None`
    """
    return _core._application

def url_for(endpoint, **args):
    """Get the URL to an endpoint.  The keyword arguments provided are used
    as URL values.  Unknown URL values are used as keyword argument.
    Additionally there are some special keyword arguments:

    `_anchor`
        This string is used as URL anchor.

    `_external`
        If set to `True` the URL will be generated with the full server name
        and `http://` prefix.
    """
    if hasattr(endpoint, 'get_url_values'):
        rv = endpoint.get_url_values()
        if rv is not None:
            if isinstance(rv, basestring):
                return make_external_url(rv)
            endpoint, updated_args = rv
            args.update(updated_args)
    anchor = args.pop('_anchor', None)
    external = args.pop('_external', False)
    rv = get_application().url_adapter.build(endpoint, args,
                                             force_external=external)
    if anchor is not None:
        rv += '#' + url_quote(anchor)
    return rv


def shared_url(spec):
    """Returns a URL to a shared resource."""
#    endpoint, filename = spec.split('::', 1)
    return url_for('static', path=spec)

def add_metanav_item(menu_item, endpoint, label, children=[]):
    get_request().metanav.append((menu_item, endpoint, label, children))

def add_navbar_item(endpoint, label):
    split_endpoint = endpoint.split('.')
    if len(split_endpoint) == 3:
        menu_item = '.'.join(split_endpoint[:-1])
    else:
        menu_item = split_endpoint[0]
    get_request().navbar.append((menu_item, endpoint, label))


def add_ctxnavbar_item(endpoint, label):
    split_endpoint = endpoint.split('.')
    if len(split_endpoint) == 3:
        menu_item = '.'.join(split_endpoint[:-1])
        submenu_item = split_endpoint[-1]
    elif len(split_endpoint) == 2:
        menu_item, submenu_item = split_endpoint
    else:
        menu_item = submenu_item = split_endpoint[0]
    get_request().ctxnavbar.setdefault(menu_item, []).append((
                                                submenu_item, endpoint, label))

def build_core_items(_active_menu_item=None):
    from ilog.privileges import ILOG_ADMIN
    request = get_request()

    # Get current active item
    _active_item = _active_menu_item and _active_menu_item or \
                                        getattr(request, 'endpoint', 'index')

    # setup metanav
#    if request.user.has_privilege(ENTER_ACCOUNT_PANEL):
    if request.user.is_somebody:
        metanav = [
            ('account', 'account.logout',
             i18n._("logout (%s)") % request.user.username),
            ('account', 'account.dashboard', i18n._("My Account"))
        ]
    else:
        metanav = [
            ('account', 'account.login', i18n._("Login")),
        ]

    if request.user.has_privilege(ILOG_ADMIN):
        metanav.append(('admin', 'admin.index', i18n._("Administration")))

    metanav.extend(request.metanav)

    # set up the navigation bar
    navigation_bar = [('index', 'index', i18n._('Home'))]

    # find out which is the correct menu and submenu bar
    active_menu = active_submenu = None
    if _active_item is not None:
        p = _active_item.split('.')
        if len(p) == 1:
            active_menu = active_submenu = p[0]
        elif len(p) >= 3:
            active_menu = '.'.join(p[:-1])
            active_submenu = p[-1]
        else:
            active_menu, active_submenu = p


    if not (active_menu.startswith('admin') or
                                            active_menu.startswith('account')):
        navigation_bar.append(('network', 'network.index', i18n._('Networks')))
    navigation_bar.extend(request.navbar)

    subnavigation_bar = request.ctxnavbar.get(active_menu, [])

    # if we are in maintenance_mode the user should know that, no matter
    # on which page he is.
    if request.app.cfg['maintenance_mode'] and \
                                        request.user.has_privilege(ILOG_ADMIN):
        flash(i18n._(u'ILog is in maintenance mode. Don\'t forget to '
                     u'turn it off again once you finish your changes.'))

    return {
        'metanav': [{'id':    endpoint,
                     'url':   url_for(endpoint),
                     'title': title,
                     'active': active_menu == menu_item
                     } for menu_item, endpoint, title in metanav],
        'navbar': [{'id':       endpoint,
                    'url':      url_for(endpoint),
                    'title':    title,
                    'active':   active_menu == menu_item
                    } for menu_item, endpoint, title in navigation_bar],
        'ctxnavbar': [{'id':       endpoint,
                       'url':      url_for(endpoint),
                       'title':    title,
                       'active':   active_submenu == submenu_item
                       } for submenu_item, endpoint, title in subnavigation_bar],
        'messages': [{
            'type':     type,
            'msg':      msg
        } for type, msg in request.session.pop('flashed_messages', [])],
        'active_pane': _active_item
    }


def select_template(templates):
    """Selects the first template from a list of templates that exists."""
    env = get_application().template_env
    for template in templates:
        if template is not None:
            try:
                return env.get_template(template)
            except TemplateNotFound:
                pass
    raise TemplateNotFound('<multiple-choices>')


def render_template(template_name, _stream=False, **context):
    """Renders a template. If `_stream` is ``True`` the return value will be
    a Jinja template stream and not an unicode object.
    This is used by `render_response`.  If the `template_name` is a list of
    strings the first template that exists is selected.
    """
    request = get_request()
    context.update({
        '_': request.translations.gettext,
        'ngettext': request.translations.ngettext,
        'core': build_core_items(context.pop('_active_menu_item', None))
    })
    if not isinstance(template_name, basestring):
        tmpl = select_template(template_name)
        template_name = tmpl.name
    else:
        tmpl = get_application().template_env.get_template(template_name)

    if _stream:
        return tmpl.stream(context)
    return tmpl.render(context)


def render_response(template_name, **context):
    """Like render_template but returns a response. If `_stream` is ``True``
    the response returned uses the Jinja stream processing. This is useful
    for pages with lazy generated content or huge output where you don't
    want the users to wait until the calculation ended. Use streaming only
    in those situations because it's usually slower than bunch processing.
    """
    return Response(render_template(template_name, **context))


class Request(RequestBase):
    """This class holds the incoming request data."""

    def __init__(self, environ, app=None):
        RequestBase.__init__(self, environ)
        self.queries = []
        self.metanav = []
        self.navbar = []
        self.ctxnavbar = {}

        if app is None:
            app = get_application()
        self.app = app

        engine = self.app.database_engine

        # get the session and try to get the user object for this request.
        from ilog.database import db, User
        user = None
        cookie_name = app.cfg['cookie_name']
        session = SecureCookie.load_cookie(self, cookie_name, app.secret_key)
        user_id = session.get('uid')
        if user_id:
            user = User.query.options(
                db.eagerload('groups'), db.eagerload('groups', 'privileges')
            ).get(user_id)
        if user is None:
            self.locale = self.app.default_locale
            self.translations = self.app.default_translations
            user = User.query.get_nobody()
        else:
            self.locale = Locale(user.locale)
            self.translations = i18n.load_translations(self.locale)
        self.user = user
        self.user.update_last_login()
        db.commit()
        self.session = session

    @property
    def is_behind_proxy(self):
        """Are we behind a proxy?"""
        return environ.get('ILOG_BEHIND_PROXY') == '1'

    def login(self, user_id, permanent=False):
        """Log the given user in. Can be user_id, username or
        a full blown user object.
        """
        log.debug("Binding user with id %r to request(%d)",
                  user_id, id(self))
        from ilog.database import db, User
        user = User.query.get(user_id)
        if user is None:
            raise RuntimeError('User does not exist')
        log.debug("Got user %r", user)
        self.user = user
        log.debug("Binding user %r to request(%d)", self.user.username, id(self))
        self.user.update_last_login()
        db.commit()
        self.session['uid'] = user.id
        self.session['lt'] = time()
        if permanent:
            self.session['pmt'] = True

    def logout(self):
        """Log the current user out."""
        from ilog.database import User
#        user = self.user
        self.user = User.query.get_nobody()
        self.session.clear()


class Response(ResponseBase):
    """This class holds the resonse data.  The default charset is utf-8
    and the default mimetype ``'text/html'``.
    """
    default_mimetype = 'text/html'


class ILog(object):

    _setup_only = []
    def setuponly(f, container=_setup_only):
        """Mark a function as "setup only".  After the setup those
        functions will be replaced with a dummy function that raises
        an exception."""
        container.append(f.__name__)
        f.__doc__ = (getdoc(f) or '') + '\n\n*This function can only be ' \
                    'called during application setup*'
        return f

    def __init__(self, instance_folder):
        # this check ensures that only setup() can create Zine instances
        if get_application() is not self:
            raise TypeError('cannot create %r instances. use the '
                            'ilog._core.setup() factory function.' %
                            self.__class__.__name__)
        self.instance_folder = path.abspath(instance_folder)

        # create the event manager, this is the first thing we have to
        # do because it could happen that events are sent during setup
        self.initialized = False

        # Setup logging
        import logging.config
        logging_file = path.join(self.instance_folder, 'logging.ini')
        if path.isfile(logging_file):
            logging.config.fileConfig(logging_file)
        del logging_file

        # and instantiate the configuration. this won't fail,
        # even if the database is not connected.
        from ilog.utils.config import Configuration
        from ilog.config import DEFAULT_VARS, HIDDEN_KEYS

        config_filename = path.join(instance_folder, 'ilog.ini')

        self.cfg = Configuration(config_filename,
                                 'ilog',
                                 DEFAULT_VARS.copy(),
                                 HIDDEN_KEYS[:])

        if not self.cfg.exists:
            raise _core.InstanceNotInitialized()

        # connect to the database
        from ilog.database import db, User
        self.database_engine = db.create_engine(
            self.cfg['database_uri'],
            self.instance_folder,
            self.cfg['database_debug']
        )

        try:
            if not self.database_engine.has_table('users'):
                raise _core.InstanceNotInitialized()
        except OperationalError, error:
            raise _core.DatabaseProblem("Database is not running??? %s" % error)

        # now setup the cache system
        self.cache = get_cache(self)

        # setup core package urls and shared stuff
        import ilog
        from ilog.urls import urls_map
        from ilog.views import all_views

        self.views = all_views.copy()
        self.url_map = urls_map

        # and create a url adapter
        scheme, netloc, script_name = urlparse(self.cfg['ilog_url'])[:3]
        self.url_adapter = self.url_map.bind(netloc, script_name,
                                             url_scheme=scheme)

        del all_views, urls_map

        # initialize default i18n/l10n system
        self.default_locale = Locale(self.cfg['language'])
        self.default_translations = i18n.load_translations(self.default_locale)

        # register the default privileges
        from ilog.privileges import DEFAULT_PRIVILEGES
        self.privileges = DEFAULT_PRIVILEGES.copy()

        env = Environment(loader=FileSystemLoader(TEMPLATE_PATH),
                          extensions=['jinja2.ext.i18n'])

        env.globals.update(
            cfg=self.cfg,
            h=htmlhelpers,
            url_for=url_for,
            static_url=shared_url,
            request=local('request'),
            ilog={
                'version':      ilog.__version__,
                'copyright':    i18n._(u'Copyright %(years)s by the ILog Team')
                                % {'years': '2010'}
            }
        )

        env.filters.update(
#            json=dump_json,
            datetime_format=i18n.format_datetime,
            date_format=i18n.format_date,
            time_format=i18n.format_time,
            timedelta_format=i18n.format_timedelta
        )

        env.install_gettext_translations(self.default_translations)
        self.template_env = env

        # now add the middleware for static file serving
        self.add_middleware(SharedDataMiddleware, {
            '/_static': SHARED_DATA,
            '/favicon.ico': SHARED_DATA
        })

        # mark the app as finished and override the setup functions
        def _error(*args, **kwargs):
            raise RuntimeError('Cannot register new callbacks after '
                               'application setup phase.')
        self.__dict__.update(dict.fromkeys(self._setup_only, _error))
        self.initialized = True

    @property
    def wants_reload(self):
        """True if the application requires a reload.  This is `True` if
        the config was changed on the file system.  A dispatcher checks this
        value every request and automatically unloads and reloads the
        application if necessary.
        """
        return self.cfg.changed_external

    @property
    def secret_key(self):
        """Returns the secret key for the instance (binary!)"""
        return self.cfg['secret_key'].encode('utf-8')

    @setuponly
    def add_middleware(self, middleware_factory, *args, **kwargs):
        """Add a middleware to the application.  The `middleware_factory`
        is a callable that is called with the active WSGI application as
        first argument, `args` as extra positional arguments and `kwargs`
        as keyword arguments.

        The newly applied middleware wraps an internal WSGI application.
        """
        self.dispatch_wsgi = middleware_factory(self.dispatch_wsgi,
                                                   *args, **kwargs)

    def list_privileges(self):
        """Return a sorted list of privileges."""
        # TODO: somehow add grouping...
        result = [(x.name, unicode(x.explanation)) for x in
                  self.privileges.values()]
        result.sort(key=lambda x: x[0] == 'ILOG_ADMIN' or x[1].lower())
        return result


    def handle_not_found(self, request, exception):
        """Handle a not found exception.  This also dispatches to plugins
        that listen for for absolute urls.  See `add_absolute_url` for
        details.
        """
        response = render_response('404.html')
        response.status_code = 404
        return response

    def send_error_notification(self, request, error):
        from pprint import pprint
        from cStringIO import StringIO
        from ilog.database import User, Privilege
        from ilog.utils.mail import send_email
        request_buffer = StringIO()
        pprint(request.__dict__, request_buffer)
        request_buffer.seek(0)
        admins = Privilege.query.get('ILOG_ADMIN').priveliged_users
        email_contents = render_template('mails/error_notification.txt',
                                         request=request_buffer.read(),
                                         error=error)
        send_email(i18n._(u"Server Error on ILog"), email_contents,
                   [admin.email for admin in admins], quiet=False)
#        from zine.notifications import send_notification_template, ZINE_ERROR
#        request_buffer = StringIO()
#        pprint(request.__dict__, request_buffer)
#        request_buffer.seek(0)
#        send_notification_template(
#            ZINE_ERROR, 'notifications/on_server_error.zeml',
#            user=request.user, summary=error.message,
#            request_details=request_buffer.read(),
#            longtext=''.join(format_exception(*sys.exc_info()))
#        )

    def handle_server_error(self, request, exc_info=None, suppress_log=False):
        """Called if a server error happens.  Logs the error and returns a
        response with an error message.
        """
        if not suppress_log:
            log.exception('Exception happened at "%s"' % request.path,
                          'core', exc_info)
        response = render_response('500.html')
        response.status_code = 500
        return response

    def handle_internal_error(self, request, error, suppress_log=True):
        """Called if internal errors are caught."""
        if request.user.is_admin:
            response = render_response('internal_error.html', error=error)
            response.status_code = 500
            return response
        # We got here, meaning no admin has seen this error yet. Notify Them!
        self.send_error_notification(request, error)
        return self.handle_server_error(request, suppress_log=suppress_log)

    def dispatch_request(self, request):
#        #! the after-request-setup event can return a response
#        #! or modify the request object in place. If we have a
#        #! response we just send it, no other modifications are done.
#        for callback in iter_listeners('after-request-setup'):
#            result = callback(request)
#            if result is not None:
#                return result

        # normal request dispatching
        try:
            try:
                endpoint, args = self.url_adapter.match(request.path)
                request.endpoint = endpoint
                response = self.views[endpoint](request, **args)
            except NotFound, e:
                response = self.handle_not_found(request, e)
            except Forbidden, e:
                if request.user.is_somebody:
                    response = render_response('403.html')
                    response.status_code = 403
                else:
                    response = _redirect(url_for('account.login',
                                                 next=request.path))
        except HTTPException, e:
            response = e.get_response(request.environ)
        except SQLAlchemyError, e:
            # Some database screw-up?! Don't let ILog stay dispatching 500's
            from ilog.database import session
            session.rollback()
            response = self.handle_internal_error(request, e,
                                                  suppress_log=False)

        # in debug mode on HTML responses we inject the collected queries.
        if self.cfg['database_debug'] and \
           getattr(response, 'mimetype', None) == 'text/html' and \
           isinstance(response.response, (list, tuple)):
            from ilog.utils.debug import inject_query_info
            inject_query_info(request, response)

        return response

    def dispatch_wsgi(self, environ, start_response):
        """This method is the internal WSGI request and is overridden by
        middlewares applied with :meth:`add_middleware`.  It handles the
        actual request dispatching.
        """
        # Create a new request object, register it with the application
        # and all the other stuff on the current thread but initialise
        # it afterwards.  We do this so that the request object can query
        # the database in the initialisation method.
        request = object.__new__(Request)
        local.request = request
        local.page_metadata = []
        local.request_locals = {}
        request.__init__(environ, self)

        # check if the blog is in maintenance_mode and the user is
        # not an administrator. in that case just show a message that
        # the user is not privileged to view the blog right now. Exception:
        # the page is the login page for the blog.
        # XXX: Remove 'admin_prefix' references for Zine 0.3
        #      It still exists because some themes might depend on it.
        admin_prefix = '/account'
        account_prefix = '/admin'
        if self.cfg['maintenance_mode'] and \
           request.path not in (account_prefix, admin_prefix) \
           and not (request.path.startswith(admin_prefix + '/') or
                    request.path.startswith(account_prefix + '/')):
            if not request.user.has_privilege(
                                        self.privileges['ENTER_ADMIN_PANEL']):
                response = render_response('maintenance.html')
                response.status_code = 503
                return response(environ, start_response)

        # if HTTPS enforcement is active, we redirect to HTTPS if
        # possible without problems (no playload)
        if self.cfg['force_https'] and request.method in ('GET', 'HEAD') and \
           environ['wsgi.url_scheme'] == 'http':
            response = _redirect('https' + request.url[4:], 301)
            return response(environ, start_response)

        # wrap the real dispatching in a try/except so that we can
        # intercept exceptions that happen in the application.
        try:
            response = self.dispatch_request(request)

            # make sure the response object is one of ours
            response = Response.force_type(response, environ)
        except InternalError, e:
            response = self.handle_internal_error(request, e)
        except:
            if self.cfg['passthrough_errors']:
                raise
            response = self.handle_server_error(request)

        # update the session cookie at the request end if the
        # session data requires an update.
        if request.session.should_save:
            # set the secret key explicitly at the end of the request
            # to not log out the administrator if he changes the secret
            # key in the config editor.
            request.session.secret_key = self.secret_key
            cookie_name = self.cfg['cookie_name']
            if request.session.get('pmt'):
                max_age = 60 * 60 * 24 * 31
                expires = time() + max_age
            else:
                max_age = expires = None
            request.session.save_cookie(response, cookie_name, max_age=max_age,
                                        expires=expires, session_expires=expires)

        return response(environ, start_response)

    def __call__(self, environ, start_response):
        """Make the application object a WSGI application."""
        return ClosingIterator(self.dispatch_wsgi(environ, start_response),
                               [local_manager.cleanup, cleanup_session])

    def __repr__(self):
        return '<ILog %r [%s]>' % (self.instance_folder, id(self))

    # remove our decorator
    del setuponly

# circular imports
from ilog.database import cleanup_session
from ilog.utils.http import make_external_url
