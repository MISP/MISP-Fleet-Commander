# from application import db
from datetime import datetime
import json
import uuid
from sqlalchemy import event, func
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.sqlite import JSON
# from application.baseModel import BaseModel
from flask_sqlalchemy import SQLAlchemy

from application.models.auth import hash_API_key

db = SQLAlchemy()
from application.baseModel import BaseModel
from application import bcrypt


def generate_uuid():
    return str(uuid.uuid4())

def init_defaults():
    if User.query.first() is None:
        user = User(email='admin@admin.test', password='Password1234', is_admin=True, must_change_password=True)
        db.session.add(user)
        db.session.commit()


class User(BaseModel):
    __tablename__ = 'users'
    id = db.Column(db.Integer,
                   primary_key=True)
    email = db.Column(db.String(80),
                      index=True,
                      unique=True,
                      nullable=False)
    created = db.Column(db.DateTime,
                        index=False,
                        unique=False,
                        nullable=False,
                        default=datetime.utcnow)
    updated = db.Column(db.DateTime,
                        index=False,
                        unique=False,
                        nullable=False,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    hashed_password = db.Column(db.String(80),
                      index=False,
                      unique=False,
                      nullable=False)
    # Only the hash of the API key is stored: the key itself is shown once, when it is generated
    apikey_hash = db.Column(db.String(64),
                            index=True,
                            nullable=True)
    is_admin = db.Column(db.Boolean,
                         nullable=False,
                         default=False,
                         server_default='0')
    # Set for accounts with a well-known password: they can only change it until they do
    must_change_password = db.Column(db.Boolean,
                                     nullable=False,
                                     default=False,
                                     server_default='0')

    user_settings = db.relationship("UserSettings", uselist=True, back_populates="user", cascade="all, delete-orphan")
    health_acks = db.relationship("HealthAck", uselist=True, cascade="all, delete-orphan")
    # Not delete-orphan: a fleet's baseline has no user, and would count as an orphan of this relationship
    saved_baselines = db.relationship("Baseline", uselist=True, back_populates="user", cascade="all")
    saved_queries = db.relationship("SavedQuery", uselist=True, back_populates="user", cascade="all, delete-orphan")

    @classmethod
    def byAPIKey(cls, apikey):
        if not apikey:
            return None
        return cls.query.filter_by(apikey_hash=hash_API_key(apikey)).first()

    def setAPIKey(self, apikey):
        self.apikey_hash = hash_API_key(apikey) if apikey else None

    @property
    def has_apikey(self):
        return self.apikey_hash is not None

    @classmethod
    def authenticate(cls, email, password_candidate):
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password_candidate):
            return user
        return None
    
    @hybrid_property
    def password(self):
        """Return the hashed user password."""
        return self.hashed_password

    @password.setter
    def password(self, password):
        self.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    def verify_password(self, candidate):
        return bcrypt.check_password_hash(self.hashed_password, candidate)


class UserSettings(BaseModel):
    __tablename__ = 'user_settings'
    settings_to_json = ['Plugins.enabled_plugins']

    id = db.Column(db.Integer,
                    primary_key=True)

    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    
    name = db.Column(db.String(120), nullable=False, index=True)
    _value = db.Column('value', db.String)
    __table_args__ = (UniqueConstraint('user_id', 'name'),)

    user = db.relationship('User', back_populates='user_settings')

    @property
    def value(self):
        if self.name in self.settings_to_json:
            try:
                decoded = json.loads(self._value)
            except:
                decoded = []
            return decoded
        return self._value

    @value.setter
    def value(self, val):
        if type(val) is list or type(val) is dict:
            val = json.dumps(val)
        self._value = val


class Server(BaseModel):
    __tablename__ = 'servers'
    id = db.Column(db.Integer,
                   primary_key=True)
    name = db.Column(db.String(120),
                     nullable=False,
                     index=True)
    uuid = db.Column(db.CHAR(36),
                     index=True,
                     unique=True,
                     nullable=False,
                     default=generate_uuid)
    comment = db.Column(db.String(256),
                     nullable=False,
                     default='')
    url = db.Column(db.String(256),
                    nullable=False,
                    index=True)
    skip_ssl = db.Column(db.Boolean,
                         nullable=False,
                         default=False)
    # Encrypted at rest: use the `authkey` property, which encrypts and decrypts
    authkey_enc = db.Column(db.Text,
                            nullable=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    fleet_id = db.Column(db.Integer,
                        db.ForeignKey('fleets.id'),
                        nullable=False,
                        index=True)
    # server_query_id = db.Column(db.Integer,
    #                     db.ForeignKey('server_queries.id'),
    #                     nullable=True,
    #                     index=True)

    user = db.relationship('User',
        backref=db.backref('servers', lazy='joined'))

    # fleet = db.relationship('Fleet',
    #     backref=db.backref('fleet', lazy='joined', uselist=True))
    fleet = db.relationship('Fleet', back_populates='servers')

    @property
    def authkey(self):
        from application import crypto
        return crypto.decrypt(self.authkey_enc)

    @authkey.setter
    def authkey(self, authkey):
        from application import crypto
        self.authkey_enc = crypto.encrypt(authkey) if authkey else None

    @hybrid_property
    def server_info(self):
        import application.models.servers as serverModel
        return serverModel.getServerInfo(self.id, True)

    @server_info.setter
    def server_info(self, info):
        self._server_info = info

    @property
    def watched_timestamp(self):
        import application.redisModel as redisModel
        return redisModel.getServerWatchedTimestamp(self.uuid)

    @property
    def connection_status(self):
        """Latest connection test, persisted in Redis"""
        import application.redisModel as redisModel
        return redisModel.getServerStatus(self.uuid)

    @watched_timestamp.setter
    def watched_timestamp(self, ts):
        self._watched_timestamp = ts


@event.listens_for(Server, 'after_delete')
def forgetDeletedServer(mapper, connection, server):
    import application.redisModel as redisModel
    try:
        redisModel.deleteServerData(server.uuid, server.id)
    except Exception as e:  # Redis being down must not prevent deleting the server
        print(f'Could not clear the cached data of server {server.uuid}: {e}')
    connection.execute(HealthAck.__table__.delete().where(HealthAck.__table__.c.server_id == server.id))
    connection.execute(MetricSample.__table__.delete().where(MetricSample.__table__.c.server_id == server.id))
    connection.execute(MetricState.__table__.delete().where(MetricState.__table__.c.server_id == server.id))
    connection.execute(SavedQueryResult.__table__.delete()
                       .where(SavedQueryResult.__table__.c.server_id == server.id))
    connection.execute(SavedQuerySample.__table__.delete()
                       .where(SavedQuerySample.__table__.c.server_id == server.id))
    connection.execute(JobResult.__table__.update().where(JobResult.__table__.c.server_id == server.id)
                       .values(server_id=None))
    from application.models.health import publishServerRemoved
    publishServerRemoved(server)


class ServerMinimal(Server):
    @hybrid_property
    def server_info(self):
        return {}

    @server_info.setter
    def server_info(self, info):
        return


class Fleet(BaseModel):
    __tablename__ = 'fleets'
    id = db.Column(db.Integer,
                   primary_key=True)
    name = db.Column(db.String(120),
                     nullable=False,
                     index=True)
    description = db.Column(db.String(2048),
                            nullable=False,
                            default='')
    is_monitored = db.Column(db.Boolean, nullable=False, server_default='0')
    is_watched = db.Column(db.Boolean, nullable=False, server_default='0')
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    timestamp = db.Column(db.Integer,
                        nullable=False,
                        index=True)

    servers = db.relationship('Server', back_populates='fleet', cascade='all, delete-orphan')
    baseline = db.relationship('Baseline', back_populates='fleet', uselist=False, cascade='all, delete-orphan')
    # servers = db.relationship('Server',
    #     backref=db.backref('fleet', lazy=True, uselist=True, nullable=False),
    #     cascade='all, delete-orphan')
    # servers = db.relationship('Server', back_populates="fleet", lazy="joined", uselist=True, cascade="all, delete-orphan")

    @hybrid_property
    def server_count(self):
        result = db.session.query(Server.fleet_id, func.count(Server.id)) \
                    .group_by(Server.fleet_id) \
                    .filter_by(fleet_id=self.id).first()
        if result is None:
            the_count = 0
        else:
            fleet_id, the_count = result
        return the_count

    @hybrid_property
    def watched_timestamp(self):
        import application.redisModel as redisModel
        return redisModel.getFleetWatchedTimestamp(self.id)

    @hybrid_property
    def monitored_timestamp(self):
        import application.redisModel as redisModel
        return redisModel.getFleetMonitoredTimestamp(self.id)

    @monitored_timestamp.setter
    def monitored_timestamp(self, ts):
        self._monitored_timestamp = ts

    @watched_timestamp.setter
    def watched_timestamp(self, ts):
        self._watched_timestamp = ts


class PinList(BaseModel):
    __tablename__ = 'pin_lists'
    id = db.Column(db.Integer,
                   primary_key=True)
    model = db.Column(db.String(120),
                     nullable=False,
                     index=True)
    uuid = db.Column(db.String(36),
                            nullable=False,
                            default='')
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)

    user = db.relationship('User',
        backref=db.backref('pinlists', lazy='joined'))
    pinlist_entries = db.relationship("PinListEntry", back_populates="pinlist", cascade="all, delete-orphan")
    # pinlist_entries = db.relationship("PinListEntry", cascade="all, delete-orphan")


class PinListEntry(BaseModel):
    __tablename__ = 'pin_list_entries'
    id = db.Column(db.Integer,
                   primary_key=True)
    pinlist_id = db.Column(db.Integer,
                   db.ForeignKey('pin_lists.id'),
                   nullable=False,
                   index=True)
    server_id = db.Column(db.Integer,
                   db.ForeignKey('servers.id'),
                   nullable=False,
                   index=True)
    data = db.Column(db.JSON,
                     nullable=False,
                     default='{}')

    pinlist = db.relationship('PinList', back_populates="pinlist_entries")
        # backref=db.backref('pinlist_entries', lazy='joined', cascade="all, delete-orphan"))


class HealthAck(BaseModel):
    """A user acknowledging a health issue: it is hidden until `until` passes, if set, or until it clears.
    `issue_first_seen` identifies the occurrence that was acknowledged: when the issue clears and comes back, it gets
    a new first-seen time and the acknowledgement no longer applies"""
    __tablename__ = 'health_acks'
    __table_args__ = (UniqueConstraint('user_id', 'issue_id'),)

    id = db.Column(db.Integer,
                   primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    server_id = db.Column(db.Integer,
                          db.ForeignKey('servers.id'),
                          nullable=False,
                          index=True)
    issue_id = db.Column(db.String(255),
                         nullable=False)
    issue_first_seen = db.Column(db.Integer,
                                 nullable=False)
    until = db.Column(db.Integer,
                      nullable=True)
    note = db.Column(db.String(500),
                     nullable=False,
                     default='')
    created = db.Column(db.Integer,
                        nullable=False)


JOB_KINDS = ('plugin_action', 'plugin_quick_action', 'rest_query', 'baseline_remediation', 'server_management',
             'edit_connection', 'organisation_copy', 'sharing_group_copy', 'mispql_query')
JOB_STATUSES = ('queued', 'running', 'done', 'partial', 'failed', 'cancelled')
# `pending` until the server's unit is over; the others are final
JOB_RESULT_STATUSES = ('pending', 'ok', 'error', 'skipped', 'cancelled')
JOB_RESULT_FINAL_STATUSES = ('ok', 'error', 'skipped', 'cancelled')


class Job(BaseModel):
    """A write sent to one or more servers, with one JobResult per server. Jobs are the audit log, so they outlive
    the user, fleet and servers they mention: those references are set to NULL on deletion (SQLite may reuse a
    deleted row's ID, which would hand the history to someone else), while the names copied at creation remain"""
    __tablename__ = 'jobs'

    id = db.Column(db.CHAR(36),
                   primary_key=True,
                   default=generate_uuid)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='SET NULL'),
                        nullable=True,
                        index=True)
    user_email = db.Column(db.String(80),
                           nullable=False,
                           default='')
    fleet_id = db.Column(db.Integer,
                         db.ForeignKey('fleets.id', ondelete='SET NULL'),
                         nullable=True,
                         index=True)
    fleet_name = db.Column(db.String(120),
                           nullable=False,
                           default='')
    kind = db.Column(db.String(32),
                     nullable=False,
                     index=True)
    title = db.Column(db.String(255),
                      nullable=False,
                      default='')
    # Redacted before being stored, for display: see application.models.jobs.redact
    params = db.Column(db.JSON,
                       nullable=False,
                       default=dict)
    # The parameters as given, encrypted at rest like server authkeys: the runner and retries need the real values.
    # Use the `secret_params` property
    params_enc = db.Column(db.Text,
                           nullable=True)
    status = db.Column(db.String(16),
                       nullable=False,
                       default='queued',
                       index=True)
    total = db.Column(db.Integer,
                      nullable=False,
                      default=0)
    succeeded = db.Column(db.Integer,
                          nullable=False,
                          default=0)
    failed = db.Column(db.Integer,
                       nullable=False,
                       default=0)
    # UNIX times, with sub-second precision for durations
    created = db.Column(db.Float,
                        nullable=False,
                        index=True)
    started = db.Column(db.Float,
                        nullable=True)
    finished = db.Column(db.Float,
                         nullable=True)

    results = db.relationship('JobResult', back_populates='job', cascade='all, delete-orphan',
                              order_by='JobResult.id')

    @property
    def secret_params(self):
        from application import crypto
        if self.params_enc is None:
            return {}
        return json.loads(crypto.decrypt(self.params_enc))

    @secret_params.setter
    def secret_params(self, params):
        from application import crypto
        self.params_enc = crypto.encrypt(json.dumps(params or {}))


class JobResult(BaseModel):
    """The outcome of a job on one server. Created `pending` with the job, so that a job lists its servers from the
    start"""
    __tablename__ = 'job_results'

    id = db.Column(db.Integer,
                   primary_key=True)
    job_id = db.Column(db.CHAR(36),
                       db.ForeignKey('jobs.id', ondelete='CASCADE'),
                       nullable=False,
                       index=True)
    server_id = db.Column(db.Integer,
                          db.ForeignKey('servers.id', ondelete='SET NULL'),
                          nullable=True,
                          index=True)
    server_name = db.Column(db.String(120),
                            nullable=False,
                            default='')
    server_url = db.Column(db.String(256),
                           nullable=False,
                           default='')
    status = db.Column(db.String(16),
                       nullable=False)
    http_status = db.Column(db.Integer,
                            nullable=True)
    summary = db.Column(db.String(1024),
                        nullable=False,
                        default='')
    # Redacted, and cut to a preview string when its JSON is too large (`response_truncated`)
    response = db.Column(db.JSON,
                         nullable=True)
    response_truncated = db.Column(db.Boolean,
                                   nullable=False,
                                   default=False,
                                   server_default='0')
    # The value replaced by the job when it is known, e.g. a setting's previous value (redacted too)
    before = db.Column(db.JSON,
                       nullable=True)
    started = db.Column(db.Float,
                        nullable=True)
    finished = db.Column(db.Float,
                         nullable=True)

    job = db.relationship('Job', back_populates='results')


BASELINE_RULE_TYPES = ('setting', 'taxonomy_enabled', 'galaxy_enabled', 'object_template_active', 'version_min',
                       'organisation', 'sharing_group', 'custom_galaxy')
BASELINE_COMPARATORS = ('eq', 'gte', 'lte')
BASELINE_SEVERITIES = ('info', 'warning', 'critical')


class Baseline(BaseModel):
    """The configuration a fleet's servers are expected to have: at most one per fleet, created with its first rule,
    deleted with the fleet. It belongs to the fleet's owner.
    A saved baseline has no fleet: it is a named set of rules of its owner (`user_id`), copied into fleets"""
    __tablename__ = 'baselines'
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_baselines_user_id_name'),)

    id = db.Column(db.Integer,
                   primary_key=True)
    fleet_id = db.Column(db.Integer,
                         db.ForeignKey('fleets.id', ondelete='CASCADE'),
                         nullable=True,
                         unique=True)
    # Saved baselines only: a fleet's baseline belongs to the fleet's owner
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=True,
                        index=True)
    name = db.Column(db.String(120),
                     nullable=True)
    description = db.Column(db.String(500),
                            nullable=False,
                            default='',
                            server_default='')
    created = db.Column(db.Integer,
                        nullable=False)
    updated = db.Column(db.Integer,
                        nullable=False)

    fleet = db.relationship('Fleet', back_populates='baseline')
    user = db.relationship('User', back_populates='saved_baselines')
    rules = db.relationship('BaselineRule', back_populates='baseline', cascade='all, delete-orphan',
                            order_by='BaselineRule.id')


class BaselineRule(BaseModel):
    """One expectation: `type` says what is checked (a setting, a taxonomy, …), `key` which one (setting name,
    taxonomy namespace, UUID of a galaxy, object template, organisation or sharing group; empty for `version_min`),
    `expected` the value it must
    have, compared with `comparator`. A drifting server raises a health issue of the rule's `severity`. Rules are
    applied in ID order when drift is fixed"""
    __tablename__ = 'baseline_rules'
    __table_args__ = (UniqueConstraint('baseline_id', 'type', 'key'),)

    id = db.Column(db.Integer,
                   primary_key=True)
    baseline_id = db.Column(db.Integer,
                            db.ForeignKey('baselines.id', ondelete='CASCADE'),
                            nullable=False,
                            index=True)
    type = db.Column(db.String(32),
                     nullable=False)
    key = db.Column(db.String(255),
                    nullable=False,
                    default='')
    # What people read for the key: a galaxy or object template name, as UUIDs are not telling
    label = db.Column(db.String(255),
                      nullable=False,
                      default='')
    expected = db.Column(db.JSON,
                         nullable=True)
    comparator = db.Column(db.String(8),
                           nullable=False,
                           default='eq')
    severity = db.Column(db.String(16),
                         nullable=False,
                         default='warning')
    note = db.Column(db.String(500),
                     nullable=False,
                     default='')
    # A setting that is usually specific to each server (its URL, its organisation, …), kept on purpose
    forced = db.Column(db.Boolean,
                       nullable=False,
                       default=False,
                       server_default='0')
    created = db.Column(db.Integer,
                        nullable=False)
    updated = db.Column(db.Integer,
                        nullable=False)

    baseline = db.relationship('Baseline', back_populates='rules')


SAVED_QUERY_COMPARATORS = ('eq', 'ne', 'lt', 'lte', 'gt', 'gte')
SAVED_QUERY_SEVERITIES = ('info', 'warning', 'critical')


class SavedQuery(BaseModel):
    """A MispQL statement kept by a user, with where it runs: a fleet (whatever servers it has when the query runs)
    or a list of servers. It may run on a schedule and say what each server's answer should be (`comparator`,
    `expected`): a server answering otherwise raises a health issue of `severity`. A saved query whose fleet was
    deleted keeps no target, and does not run"""
    __tablename__ = 'saved_queries'
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_saved_queries_user_id_name'),)

    id = db.Column(db.Integer,
                   primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False,
                        index=True)
    name = db.Column(db.String(120),
                     nullable=False)
    description = db.Column(db.String(500),
                            nullable=False,
                            default='',
                            server_default='')
    statement = db.Column(db.Text,
                          nullable=False)
    fleet_id = db.Column(db.Integer,
                         db.ForeignKey('fleets.id', ondelete='SET NULL'),
                         nullable=True,
                         index=True)
    server_ids = db.Column(db.JSON,
                           nullable=True)
    # Minutes between runs; None: run by hand only
    schedule_minutes = db.Column(db.Integer,
                                 nullable=True)
    # What each server's count (or number of rows) should be; None: no expectation
    comparator = db.Column(db.String(8),
                           nullable=True)
    expected = db.Column(db.BigInteger,
                         nullable=True)
    severity = db.Column(db.String(16),
                         nullable=False,
                         default='warning',
                         server_default='warning')
    created = db.Column(db.Integer,
                        nullable=False)
    updated = db.Column(db.Integer,
                        nullable=False)
    # When the last run started, scheduled or by hand, and its job (which job retention may have deleted since)
    last_run_at = db.Column(db.Integer,
                            nullable=True)
    last_job_id = db.Column(db.CHAR(36),
                            nullable=True)
    # Why the last scheduled run could not start, e.g. no server left
    last_error = db.Column(db.String(255),
                           nullable=False,
                           default='',
                           server_default='')

    user = db.relationship('User', back_populates='saved_queries')
    results = db.relationship('SavedQueryResult', back_populates='saved_query', cascade='all, delete-orphan',
                              order_by='SavedQueryResult.id')


class SavedQueryResult(BaseModel):
    """What one server answered to a saved query the last time it ran there: never its rows, only the outcome of the
    run on that server (see models/fleetQueries.py) and the number it gave, a count or the rows returned"""
    __tablename__ = 'saved_query_results'
    __table_args__ = (UniqueConstraint('saved_query_id', 'server_id', name='uq_saved_query_results_query_server'),)

    id = db.Column(db.Integer,
                   primary_key=True)
    saved_query_id = db.Column(db.Integer,
                               db.ForeignKey('saved_queries.id', ondelete='CASCADE'),
                               nullable=False,
                               index=True)
    server_id = db.Column(db.Integer,
                          db.ForeignKey('servers.id', ondelete='CASCADE'),
                          nullable=False,
                          index=True)
    job_id = db.Column(db.CHAR(36),
                       nullable=True)
    outcome = db.Column(db.String(32),
                        nullable=False)
    value = db.Column(db.BigInteger,
                      nullable=True)
    # More rows on the server than the LIMIT let through
    more = db.Column(db.Boolean,
                     nullable=False,
                     default=False,
                     server_default='0')
    message = db.Column(db.String(500),
                        nullable=False,
                        default='',
                        server_default='')
    checked_at = db.Column(db.Integer,
                           nullable=False)

    saved_query = db.relationship('SavedQuery', back_populates='results')


SAVED_QUERY_SAMPLE_TIERS = ('raw', 'day')


class SavedQuerySample(BaseModel):
    """The history of a saved query on a server: the numbers it answered over time, never its rows. A `raw` row is
    one answer, timed when the server gave it. A `day` row sums up the answers of the UTC day starting at `ts`: the
    last one (`value`), the lowest and highest, how many there were (`samples`). `more` marks a SELECT that found more
    rows than its LIMIT let through (on a day row: at least once that day)"""
    __tablename__ = 'saved_query_samples'
    __table_args__ = (UniqueConstraint('saved_query_id', 'server_id', 'tier', 'ts',
                                       name='uq_saved_query_samples_query_server_tier_ts'),
                      db.Index('ix_saved_query_samples_tier_ts', 'tier', 'ts'))

    id = db.Column(db.Integer,
                   primary_key=True)
    saved_query_id = db.Column(db.Integer,
                               db.ForeignKey('saved_queries.id', ondelete='CASCADE'),
                               nullable=False)
    server_id = db.Column(db.Integer,
                          db.ForeignKey('servers.id', ondelete='CASCADE'),
                          nullable=False)
    tier = db.Column(db.String(8),
                     nullable=False)
    ts = db.Column(db.Integer,
                   nullable=False)
    value = db.Column(db.BigInteger,
                      nullable=False)
    low = db.Column(db.BigInteger,
                    nullable=True)
    high = db.Column(db.BigInteger,
                     nullable=True)
    samples = db.Column(db.Integer,
                        nullable=False,
                        default=1,
                        server_default='1')
    more = db.Column(db.Boolean,
                     nullable=False,
                     default=False,
                     server_default='0')

    def __repr__(self):
        return f"<SavedQuerySample>(saved_query_id={self.saved_query_id!r}, server_id={self.server_id!r}, " \
               f"tier={self.tier!r}, ts={self.ts!r})"


METRIC_TIERS = ('raw', 'hour', 'day')


class MetricSample(BaseModel):
    """Usage metrics of a server at one time. `raw` rows are single collections, timed when they were stored; `hour`
    and `day` rows sum them up over the bucket starting at `ts` (UTC), from `samples` raw rows. `values` maps metric
    keys (see models/metricCatalogue.py) to numbers and only holds the keys that were read; `peaks` holds the
    maximum of each gauge over a bucket"""
    __tablename__ = 'metric_samples'
    __table_args__ = (UniqueConstraint('server_id', 'tier', 'ts', name='uq_metric_samples_server_tier_ts'),
                      db.Index('ix_metric_samples_tier_ts', 'tier', 'ts'))

    id = db.Column(db.Integer,
                   primary_key=True)
    server_id = db.Column(db.Integer,
                          db.ForeignKey('servers.id'),
                          nullable=False)
    tier = db.Column(db.String(8),
                     nullable=False)
    ts = db.Column(db.Integer,
                   nullable=False)
    values = db.Column(db.JSON,
                       nullable=False,
                       default=dict)
    peaks = db.Column(db.JSON,
                      nullable=True)
    samples = db.Column(db.Integer,
                        nullable=False,
                        default=1)


class MetricState(BaseModel):
    """Where the metric collection of a server stands: when it was last tried and how it went, and the MISP log id
    up to which logins have been counted"""
    __tablename__ = 'metric_states'

    server_id = db.Column(db.Integer,
                          db.ForeignKey('servers.id'),
                          primary_key=True,
                          autoincrement=False)
    login_cursor = db.Column(db.Integer,
                             nullable=True)
    logins_backfilled = db.Column(db.Boolean,
                                  nullable=False,
                                  default=False,
                                  server_default='0')
    logins_read_at = db.Column(db.Integer,
                               nullable=True)
    logins_total = db.Column(db.Integer,
                             nullable=False,
                             default=0,
                             server_default='0')
    failed_logins_total = db.Column(db.Integer,
                                    nullable=False,
                                    default=0,
                                    server_default='0')
    last_attempt = db.Column(db.Integer,
                             nullable=True)
    last_success = db.Column(db.Integer,
                             nullable=True)
    last_error = db.Column(db.String(500),
                           nullable=True)

    def __repr__(self):
        return f"<MetricState>(server_id={self.server_id!r})"


# SQLite does not enforce foreign keys here, so the ON DELETE clauses above are applied by these listeners
@event.listens_for(User, 'after_delete')
def detachDeletedUserJobs(mapper, connection, user):
    connection.execute(Job.__table__.update().where(Job.__table__.c.user_id == user.id).values(user_id=None))


@event.listens_for(Fleet, 'after_delete')
def detachDeletedFleetJobs(mapper, connection, fleet):
    connection.execute(Job.__table__.update().where(Job.__table__.c.fleet_id == fleet.id).values(fleet_id=None))


@event.listens_for(SavedQuery, 'after_delete')
def forgetDeletedQueryHistory(mapper, connection, saved):
    """In bulk: a saved query run every 15 minutes holds thousands of rows"""
    connection.execute(SavedQuerySample.__table__.delete()
                       .where(SavedQuerySample.__table__.c.saved_query_id == saved.id))


@event.listens_for(Fleet, 'after_delete')
def detachDeletedFleetQueries(mapper, connection, fleet):
    """Saved queries aimed at the fleet are the user's work: they stay, without target"""
    connection.execute(SavedQuery.__table__.update().where(SavedQuery.__table__.c.fleet_id == fleet.id)
                       .values(fleet_id=None))
