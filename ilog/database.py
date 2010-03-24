# -*- coding: utf-8 -*-
"""
    ilog.database
    ~~~~~~~~~~~~~
    This module is a layer on top of SQLAlchemy to provide asynchronous
    access to the database and has the used tables/models used in ILog.

    :copyright: © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import os
import sys
import logging
from hashlib import md5, sha1
from time import time
from types import ModuleType
from datetime import datetime, timedelta

import sqlalchemy
from sqlalchemy import and_, or_
from sqlalchemy import orm, schema
from sqlalchemy.interfaces import ConnectionProxy
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (EXT_CONTINUE, MapperExtension, dynamic_loader,
                            deferred)

#from ilog import application as app
from ilog.utils import local_manager, gen_ascii_slug
from ilog.utils.crypto import gen_pwhash, check_pwhash

log = logging.getLogger(__name__)

def get_engine():
    """Return the active database engine (the database engine of the active
    application).  If no application is enabled this has an undefined behavior.
    If you are not sure if the application is bound to the active thread, use
    :func:`~zine.application.get_application` and check it for `None`.
    The database engine is stored on the application object as `database_engine`.
    """
    from ilog.application import get_application
    return get_application().database_engine

def create_engine(uri, relative_to=None, debug=False):
    """Create a new engine.  This works a bit like SQLAlchemy's
    `create_engine` with the difference that it automaticaly set's MySQL
    engines to 'utf-8', and paths for SQLite are relative to the path
    provided as `relative_to`.

    Furthermore the engine is created with `convert_unicode` by default.
    """
    # special case sqlite.  We want nicer urls for that one.
    if uri.startswith('sqlite:'):
        raise Exception("Sqlite database not supported")
#        match = _sqlite_re.match(uri)
#        if match is None:
#            raise ArgumentError('Could not parse rfc1738 URL')
#        database, query = match.groups()
#        if database is None:
#            database = ':memory:'
#        elif relative_to is not None:
#            database = path.join(relative_to, database)
#        if query:
#            query = url_decode(query).to_dict()
#        else:
#            query = {}
#        info = URL('sqlite', database=database, query=query)

    else:
        info = make_url(uri)

        # if mysql is the database engine and no connection encoding is
        # provided we set it to utf-8
        if info.drivername == 'mysql':
            info.query.setdefault('charset', 'utf8')

    options = {'convert_unicode': True}

    # alternative pool sizes / recycle settings and more.  These are
    # interpreter wide and not from the config for the following reasons:
    #
    # - system administrators can set it independently from the webserver
    #   configuration via SetEnv and friends.
    # - this setting is deployment dependent should not affect a development
    #   server for the same instance or a development shell
    for key in 'pool_size', 'pool_recycle', 'pool_timeout':
        value = os.environ.get('ILOG_DATABASE_' + key.upper())
        if value is not None:
            options[key] = int(value)

    # if debugging is enabled, hook the ConnectionDebugProxy in
    if debug:
        options['proxy'] = ConnectionDebugProxy()
    return sqlalchemy.create_engine(info, **options)

class ConnectionDebugProxy(ConnectionProxy):
    """Helps debugging the database."""

    def cursor_execute(self, execute, cursor, statement, parameters,
                       context, executemany):
        start = time()
        try:
            return execute(cursor, statement, parameters, context)
        finally:
            from ilog.application import get_request
            from ilog.utils.debug import find_calling_context
            request = get_request()
            if request is not None:
                request.queries.append((statement, parameters, start,
                                        time(), find_calling_context()))

#: create a new module for all the database related functions and objects
sys.modules['ilog.database.db'] = db = ModuleType('db')
key = value = mod = None
for mod in sqlalchemy, orm:
    for key, value in mod.__dict__.iteritems():
        if key == 'create_engine':
            continue
        if key in mod.__all__:
            setattr(db, key, value)
del key, mod, value
db.and_ = and_
db.or_ = or_
#del and_, or_


db.create_engine = create_engine
db.DeclarativeBase = DeclarativeBase = declarative_base()
db.metadata = metadata = DeclarativeBase.metadata

db.session = session = orm.scoped_session(
    lambda: orm.create_session(get_engine(), autoflush=True, autocommit=False),
                                local_manager.get_ident)

#: forward some session methods to the module as well
for name in 'delete', 'save', 'flush', 'execute', 'begin', 'mapper', \
            'commit', 'rollback', 'clear', 'refresh', 'expire', \
            'query_property':
    setattr(db, name, getattr(session, name))
#: called at the end of a request
db.cleanup_session = cleanup_session = session.remove


log = logging.getLogger(__name__)

class _ModelBase(object):
    # Query Object
    query         = session.query_property(orm.Query)

    def __repr__(self):
        return "<%s %d>" % (self.__class__.__name__,
                            getattr(self, 'id', id(self)))


class Provider(DeclarativeBase, _ModelBase):
    __tablename__ = 'providers'

    identifier    = db.Column(db.String, primary_key=True)
    provider      = db.Column(db.String(25), index=True, unique=True)
    user_id       = db.Column(db.ForeignKey("users.id"))

    # Relationships
    account       = None    # Defined on User

    def __init__(self, identifier=None, provider=None):
        self.identifier = identifier
        self.provider = provider


class UserQuery(orm.Query):

    def get_nobody(self):
        return AnonymousUser()

    def too_old_activations(self):
        return self.filter(
            db.and_(User.active==False,
                 User.register_date<=datetime.utcnow()-timedelta(days=30)
            )
        )

    def by_provider(self, identifier):
        provider = Provider.query.get(identifier)
        if provider:
            return provider.account
        return None


class User(DeclarativeBase, _ModelBase):
    __tablename__ = 'users'

    is_somebody   = True

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(25), index=True, unique=True)
    email         = db.deferred(db.Column(db.String, index=True, unique=True))
    display_name  = db.Column(db.String(60))
    banned        = db.Column(db.Boolean, default=False)
    confirmed     = db.Column(db.Boolean, default=False)
    passwd_hash   = db.Column(db.String, default="!")
    last_login    = db.Column(db.DateTime, default=datetime.utcnow)
    register_date = orm.deferred(db.Column(db.DateTime,
                                           default=datetime.utcnow))
    activation_key= db.Column(db.String, default="!")
    tzinfo        = db.Column(db.String(25), default="UTC")
    locale        = db.Column(db.String(10), default="en")


    # Relationships
    privileges    = db.relation("Privilege", secondary="user_privileges",
                                backref="priveliged_users", lazy=True,
                                collection_class=set, cascade='all, delete')
    groups        = None    # Defined on Group
    providers     = db.relation("Provider", backref="account",
                                collection_class=set,
                                cascade="all, delete, delete-orphan")
    identities    = None    # Defined on Identity

    query   = session.query_property(UserQuery)

    def __init__(self, username=None, email=None, display_name=None,
                 confirmed=False, passwd=None, tzinfo="UTC", locale="en"):
        self.username = username
        self.display_name = display_name and display_name or username
        self.email = email
        self.confirmed = confirmed
        if passwd:
            self.set_password(passwd)

    def __repr__(self):
        return "<User %s>" % (self.username or 'annonymous')

    def _active(self):
        return self.activation_key == '!'
    active = property(_active)

    def set_activation_key(self):
        self.activation_key = sha1(("%s|%s|%s|%s" % (
            self.id, self.username, self.register_date, time())).encode('utf-8')
        ).hexdigest()

    def activate(self):
        self.activation_key = '!'

    def get_gravatar_url(self, size=80):
        from ilog.application import get_application
        assert 8 < size < 256, 'unsupported dimensions'
        return '%s/%s?d=%s&rating=%s&size=%d' % (
            get_application().cfg['gravatar/url'].rstrip('/'),
            md5(self.email.lower()).hexdigest(),
            get_application().cfg['gravatar/fallback'],
            get_application().cfg['gravatar/rating'],
            size
        )
    gravatar_url = property(get_gravatar_url)

    def set_password(self, password):
        self.passwd_hash = gen_pwhash(password)

    def check_password(self, password):
        if self.passwd_hash == '!':
            return False
        if check_pwhash(self.passwd_hash, password):
            self.update_last_login()
            return True
        return False

    def update_last_login(self):
        self.last_login = datetime.utcnow()

    @property
    def all_privileges(self):
        from ilog.application import get_application
        result = set(self.privileges)
        for group in self.groups:
            result.update(group.privileges)
        return frozenset([get_application().privileges.get(p.name)
                          for p in result])

    def has_privilege(self, privilege):
        return add_privilege(privilege)(self.all_privileges)

    @property
    def is_admin(self):
        return self.has_privilege(ILOG_ADMIN)

    @property
    def is_manager(self):
        return self.has_privilege(ENTER_ADMIN_PANEL)


class AnonymousUser(User):
    is_somebody   = False
    locale        = 'en'


class PrivilegeQuery(orm.Query):

    def get(self, privilege):
        if not isinstance(privilege, basestring):
            privilege = privilege.name
        return self.filter(Privilege.name==privilege).first()


class Privilege(DeclarativeBase, _ModelBase):
    __tablename__ = 'privileges'

    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(50), unique=True)

    query   = session.query_property(PrivilegeQuery)

    def __init__(self, privilege_name):
        if not isinstance(privilege_name, basestring):
            privilege_name = privilege_name.name
        self.name = privilege_name

    @property
    def privilege(self):
        from ilog.application import get_application
        return get_application().privileges.get(self.name)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)


user_privileges = db.Table('user_privileges', metadata,
    db.Column('user_id', db.ForeignKey('users.id')),
    db.Column('privilege_id', db.ForeignKey('privileges.id'))
)


class Group(DeclarativeBase, _ModelBase):
    __tablename__ = 'groups'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(30))

    users         = db.dynamic_loader("User", backref=db.backref("groups",
                                                                 lazy=True),
                                      secondary="group_users",
                                      query_class=UserQuery)
    privileges    = db.relation("Privilege", secondary="group_privileges",
                                backref="priveliged_groups", lazy=True,
                                collection_class=set, cascade='all, delete')

    def __init__(self, group_name):
        self.name = group_name

    def __repr__(self):
        return u'<%s %r:%r>' % (self.__class__.__name__, self.id, self.name)


group_users = db.Table('group_users', metadata,
    db.Column('group_id', db.ForeignKey('groups.id')),
    db.Column('user_id', db.ForeignKey('users.id'))
)

group_privileges = db.Table('group_privileges', metadata,
    db.Column('group_id', db.ForeignKey('groups.id')),
    db.Column('privilege_id', db.ForeignKey('privileges.id'))
)


class Bot(DeclarativeBase, _ModelBase):
    __tablename__ = 'bots'

    name    = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.ForeignKey('users.id'))


class Network(DeclarativeBase, _ModelBase):
    __tablename__ = 'networks'

    slug    = db.Column(db.String, primary_key=True)
    name    = db.Column(db.String(20))

    # Relationships
    servers = db.relation("NetworkServer", backref="network",
                          cascade="all, delete, delete-orphan")
    participations = db.relation("NetworkParticipation", backref="network",
                                 cascade="all, delete, delete-orphan")

    def __init__(self, name):
        self.name = name
        self.slug = self.__create_slug(name)

    def __create_slug(self, name):
        initial_slug = gen_ascii_slug(name)
        slug = initial_slug
        similiars = 1
        sa_session = db.session()
        while sa_session.query(Network).filter(Network.slug==slug).first():
            slug = "%s-%i" % (initial_slug, similiars)
            similiars += 1
        sa_session.close()
        return slug


class NetworkServer(DeclarativeBase, _ModelBase):
    __tablename__  = 'network_servers'
    __table_args__ = (db.UniqueConstraint('network_slug', 'address', 'port'), {})

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    network_slug   = db.Column(db.ForeignKey('networks.slug'))
    address        = db.Column(db.String, nullable=False)
    port           = db.Column(db.Integer, nullable=False)
    lag            = db.Column(db.Float, default=0.0)
    conn_failures  = db.Column(db.Integer, default=0)
    failure_msg    = db.Column(db.String, nullable=True)

    def __init__(self, address, port):
        self.address = address
        self.port = port


class NetworkParticipation(DeclarativeBase, _ModelBase):
    __tablename__ = 'network_participations'
#    __table_args__ = (db.UniqueConstraint('bot_id', 'network_slug'), {})

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bot_id        = db.Column(db.ForeignKey('bots.name'))
    network_slug  = db.Column(db.ForeignKey('networks.slug'))
    nick          = db.Column(db.String, nullable=False)
    password      = db.Column(db.String)


class IrcIdentity(DeclarativeBase, _ModelBase):
    __tablename__  = 'identities'
    __table_args__ = (db.UniqueConstraint('network_name', 'nick'), {})

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    network_name   = db.Column(db.ForeignKey('networks.slug'))
    nick           = db.Column(db.String(64))
    realname       = db.Column(db.String(128))
    ident          = db.Column(db.String(64))
    user_id        = db.Column(db.ForeignKey('users.id'), default=None)


class Channel(DeclarativeBase, _ModelBase):
    __tablename__  = 'channels'
    __table_args__ = (db.UniqueConstraint('network_name', 'name', 'prefix'), {})

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name           = db.Column(db.String, index=True)
    network_name   = db.Column(db.ForeignKey('networks.slug'), index=True)
    prefix         = db.Column(db.String(3))
#    locale         = db.Column(db.String(6))
    key            = db.Column(db.String, nullable=True)

    # Topic Related
    topic         = db.Column(db.String)
    changed_on    = db.Column('topic_changed_on', db.DateTime(timezone=True))
    changed_by_id = db.Column('topic_changed_by_identity_id',
                              db.ForeignKey('identities.id'))


class IrcEvent(DeclarativeBase, _ModelBase):
    __tablename__  = 'irc_events'
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id     = db.Column(db.ForeignKey('channels.id'), index=True)
    stamp          = db.Column(db.DateTime(timezone=True))
    type           = db.Column(db.String(10))
    identity_id    = db.Column(db.ForeignKey('identities.id'), index=True)
    message        = db.Column(db.String)


# circular imports
from ilog.privileges import (add_privilege, ILOG_ADMIN, ENTER_ADMIN_PANEL,
                             ENTER_ACCOUNT_PANEL)
