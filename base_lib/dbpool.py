
# coding: utf-8
import os, sys, time, datetime
import types, random
import threading
import logging  as log

debug = True
dbpool = {}


class DBPoolBase:
    def acquire(self, name):
        pass

    def release(self, name, conn):
        pass


class DBResult:
    def __init__(self, fields, data):
        self.fields = fields
        self.data = data

    def todict(self):
        ret = []
        for item in self.data:
            ret.append(dict(zip(self.fields, item)))
        return ret

    def __iter__(self):
        for row in self.data:
            yield dict(zip(self.fields, row))

    def row(self, i, isdict=True):
        if isdict:
            return dict(zip(self.fields, self.data[i]))
        return self.data[i]

    def __getitem__(self, i):
        return dict(zip(self.fields, self.data[i]))


class DBFunc:
    def __init__(self, data):
        self.value = data


class DBConnection:
    def __init__(self, param, lasttime, status):
        self.name = None
        self.param = param
        self.conn = None
        self.status = status
        self.lasttime = lasttime

    def is_available(self):
        if self.status == 0:
            return True
        return False

    def useit(self):
        self.status = 1
        self.lasttime = time.time()

    def releaseit(self):
        self.status = 0

    def connect(self):
        pass

    def close(self):
        pass

    def alive(self):
        pass

    def cursor(self):
        return self.conn.cursor()

    def execute(self, sql, param=None):

        if debug:
            log.info('exec:%s', sql)
        cur = self.conn.cursor()
        try:
            if param:
                ret = cur.execute(sql, param)
            else:
                ret = cur.execute(sql)
        except:
            self.connect()
            if param:
                ret = cur.execute(sql, param)
            else:
                ret = cur.execute(sql)
        cur.close()
        return ret

    def executemany(self, sql, param):
        cur = self.conn.cursor()
        try:
            ret = cur.executemany(sql, param)
        except:
            self.connect()
            ret = cur.executemany(sql, param)
        cur.close()
        return ret

    def query(self, sql, param=None, isdict=True):
        '''sql查询，返回查询结果'''
        if debug:
            log.info('query:%s', sql)
        cur = self.conn.cursor()
        try:
            if not param:
                cur.execute(sql)
            else:
                cur.execute(sql, param)
        except:
            self.connect()
            if not param:
                cur.execute(sql)
            else:
                cur.execute(sql, param)
        res = cur.fetchall()
        cur.close()
        # log.info('desc:', cur.description)
        if res and isdict:
            ret = []
            xkeys = [i[0] for i in cur.description]
            for item in res:
                ret.append(dict(zip(xkeys, item)))
        else:
            ret = res
        return ret

    def get(self, sql, param=None, isdict=True):
        '''sql查询，只返回一条'''
        cur = self.conn.cursor()
        try:
            if not param:
                cur.execute(sql)
            else:
                cur.execute(sql, param)
        except:
            self.connect()
            if not param:
                cur.execute(sql)
            else:
                cur.execute(sql, param)
        res = cur.fetchone()
        cur.close()
        if res and isdict:
            xkeys = [i[0] for i in cur.description]
            return dict(zip(xkeys, res))
        else:
            return res

    def value2sql(self, v, charset='utf-8'):
        tv = type(v)
        if tv in [types.StringType, types.UnicodeType]:
            if tv == types.UnicodeType:
                v = v.encode(charset)
            if v.startswith(('now()', 'md5(')):
                return v
            return "'%s'" % self.escape(v)
        elif isinstance(v, datetime.datetime):
            return "'%s'" % str(v)
        elif isinstance(v, DBFunc):
            return v.value
        else:
            if v is None:
                return 'NULL'
            return str(v)

    def dict2sql(self, d, sp=','):
        x = []
        for k, v in d.iteritems():
            x.append('%s=%s' % (k, self.value2sql(v)))
        return sp.join(x)

    def dict2insert(self, d):
        keys = d.keys()
        vals = []
        for k in keys:
            vals.append('%s' % self.value2sql(d[k]))
        return ','.join(keys), ','.join(vals)

    def insert(self, table, values):
        # sql = "insert into %s set %s" % (table, self.dict2sql(values))
        keys, vals = self.dict2insert(values)
        sql = "insert into %s(%s) values (%s)" % (table, keys, vals)
        ret = self.execute(sql)
        if ret:
            ret = self.last_insert_id()
        return ret

    def insert_ignore(self, table, values):
        keys, vals = self.dict2insert(values)
        sql = "insert ignore into %s(%s) values (%s)" % (table, keys, vals)
        ret = self.execute(sql)
        if ret:
            ret = self.last_insert_id()
        return ret

    def update(self, table, values, where=None):
        sql = "update %s set %s" % (table, self.dict2sql(values))
        if where:
            sql += " where %s" % self.dict2sql(where, ' and ')
        return self.execute(sql)

    def delete(self, table, where):
        sql = "delete from %s" % table
        if where:
            sql += " where %s" % self.dict2sql(where, ' and ')
        return self.execute(sql)

    def select(self, table, where=None, fields='*', other=None, isdict=True):
        sql = "select %s from %s" % (fields, table)
        if where:
            sql += " where %s" % self.dict2sql(where, ' and ')
        if other:
            sql += ' ' + other
        return self.query(sql, None, isdict=isdict)

    def select_sql(self, table, where=None, fields='*', other=None):
        if type(fields) in (types.ListType, types.TupleType):
            fields = ','.join(fields)
        sql = "select %s from %s" % (fields, table)
        if where:
            sql += " where %s" % self.dict2sql(where, ' and ')
        if other:
            sql += ' ' + other
        return sql

    def last_insert_id(self):
        pass

    def start(self):  # start transaction
        pass

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def escape(self, s):
        return s


def with_mysql_reconnect(func):
    def _(self, *args, **argitems):
        import MySQLdb

        trycount = 3
        while True:
            try:
                x = func(self, *args, **argitems)
            except MySQLdb.OperationalError, e:
                # log.err('mysql error:', e)
                if e[0] >= 2000:  # client error
                    # log.err('reconnect ...')
                    self.conn.close()
                    self.connect()

                    trycount -= 1
                    if trycount > 0:
                        continue
                raise
            else:
                return x

    return _


def with_pg_reconnect(func):
    def _(self, *args, **argitems):
        import psycopg2

        trycount = 3
        while True:
            try:
                x = func(self, *args, **argitems)
            except psycopg2.OperationalError, e:
                # log.err('mysql error:', e)
                if e[0] >= 2000:  # client error
                    # log.err('reconnect ...')
                    self.conn.close()
                    self.connect()

                    trycount -= 1
                    if trycount > 0:
                        continue
                raise
            else:
                return x

    return _


class PGConnection(DBConnection):
    name = "pg"

    def __init__(self, param, lasttime, status):
        DBConnection.__init__(self, param, lasttime, status)

        self.connect()

    def useit(self):
        self.status = 1
        self.lasttime = time.time()

    def releaseit(self):
        self.status = 0

    def connect(self):
        engine = self.param['engine']
        if engine == 'pg':
            import psycopg2

            self.conn = psycopg2.connect(host=self.param['host'],
                                         port=self.param['port'],
                                         user=self.param['user'],
                                         password=self.param['passwd'],
                                         database=self.param['db']
                                         )
            self.conn.autocommit = 1
        else:
            raise ValueError, 'engine error:' + engine
            # log.note('mysql connected', self.conn)

    def close(self):
        self.conn.close()
        self.conn = None

    @with_pg_reconnect
    def alive(self):
        if self.is_available():
            cur = self.conn.cursor()
            cur.query("show tables;")
            cur.close()
            self.conn.ping()

    @with_pg_reconnect
    def execute(self, sql, param=None):
        return DBConnection.execute(self, sql, param)

    @with_pg_reconnect
    def executemany(self, sql, param):
        return DBConnection.executemany(self, sql, param)

    @with_pg_reconnect
    def query(self, sql, param=None, isdict=True):
        return DBConnection.query(self, sql, param, isdict)

    @with_pg_reconnect
    def get(self, sql, param=None, isdict=True):
        return DBConnection.get(self, sql, param, isdict)

    def escape(self, s, enc='utf-8'):
        if type(s) == types.UnicodeType:
            s = s.encode(enc)
        import psycopg2

        ns = psycopg2._param_escape(s)
        return unicode(ns, enc)

    def last_insert_id(self):
        ret = self.query('select last_insert_id()', isdict=False)
        return ret[0][0]

    def start(self):
        sql = "start transaction"
        return self.execute(sql)

    def insert(self, table, values):
        # sql = "insert into %s set %s" % (table, self.dict2sql(values))
        ret = 0
        try:
            keys, vals = self.dict2insert(values)
            sql = "insert into %s(%s) values (%s) RETURNING id" % (table, keys, vals)
            data = self.query(sql)
            if data:
                ret = data[0].get('id')
        except Exception, e:
            log.error(e)
        return ret

    def insert_ignore(self, table, values):
        return self.insert(table, values)


class MySQLConnection(DBConnection):
    name = "mysql"

    def __init__(self, param, lasttime, status):
        DBConnection.__init__(self, param, lasttime, status)

        self.connect()

    def useit(self):
        self.status = 1
        self.lasttime = time.time()

    def releaseit(self):
        self.status = 0

    def connect(self):
        engine = self.param['engine']
        if engine == 'mysql':
            import MySQLdb

            self.conn = MySQLdb.connect(host=self.param['host'],
                                        port=self.param['port'],
                                        user=self.param['user'],
                                        passwd=self.param['passwd'],
                                        db=self.param['db'],
                                        charset=self.param['charset'],
                                        connect_timeout=self.param.get('timeout', 0),
                                        )

            self.conn.autocommit(1)

            # if self.param.get('autocommit',None):
            #    log.note('set autocommit')
            #    self.conn.autocommit(1)
            # initsqls = self.param.get('init_command')
            # if initsqls:
            #    log.note('init sqls:', initsqls)
            #    cur = self.conn.cursor()
            #    cur.execute(initsqls)
            #    cur.close()
        else:
            raise ValueError, 'engine error:' + engine
            # log.note('mysql connected', self.conn)

    def close(self):
        self.conn.close()
        self.conn = None

    @with_mysql_reconnect
    def alive(self):
        if self.is_available():
            cur = self.conn.cursor()
            cur.execute("show tables;")
            cur.close()
            self.conn.ping()

    @with_mysql_reconnect
    def execute(self, sql, param=None):
        return DBConnection.execute(self, sql, param)

    @with_mysql_reconnect
    def executemany(self, sql, param):
        return DBConnection.executemany(self, sql, param)

    @with_mysql_reconnect
    def query(self, sql, param=None, isdict=True):
        return DBConnection.query(self, sql, param, isdict)

    @with_mysql_reconnect
    def get(self, sql, param=None, isdict=True):
        return DBConnection.get(self, sql, param, isdict)

    def escape(self, s, enc='utf-8'):
        if type(s) == types.UnicodeType:
            s = s.encode(enc)
        ns = self.conn.escape_string(s)
        return unicode(ns, enc)

    def last_insert_id(self):
        ret = self.query('select last_insert_id()', isdict=False)
        return ret[0][0]

    def start(self):
        sql = "start transaction"
        return self.execute(sql)


class SQLiteConnection(DBConnection):
    name = "sqlite"

    def __init__(self, param, lasttime, status):
        DBConnection.__init__(self, param, lasttime, status)

    def connect(self):
        engine = self.param['engine']
        if engine == 'sqlite':
            import sqlite3

            self.conn = sqlite3.connect(self.param['db'], isolation_level=None)
        else:
            raise ValueError, 'engine error:' + engine

    def useit(self):
        DBConnection.useit(self)
        if not self.conn:
            self.connect()

    def releaseit(self):
        DBConnection.releaseit(self)
        self.conn.close()
        self.conn = None

    def escape(self, s, enc='utf-8'):
        s = s.replace("'", "\\'")
        s = s.replace('"', '\\"')
        return s

    def last_insert_id(self):
        ret = self.query('select last_insert_rowid()', isdict=False)
        return ret[0][0]

    def start(self):
        sql = "BEGIN"
        return self.conn.execute(sql)


class DBPool(DBPoolBase):
    def __init__(self, dbcf):
        # one item: [conn, last_get_time, stauts]
        self.dbconn_idle = []
        self.dbconn_using = []

        self.dbcf = dbcf
        self.max_conn = 10
        self.min_conn = 1

        if self.dbcf.has_key('conn'):
            self.max_conn = self.dbcf['conn']

        self.connection_class = {}
        x = globals()
        for v in x.itervalues():
            if type(v) == types.ClassType and v != DBConnection and issubclass(v, DBConnection):
                self.connection_class[v.name] = v

        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

        self.open(self.min_conn)

    def synchronize(func):
        def _(self, *args, **argitems):
            self.lock.acquire()
            x = None
            try:
                x = func(self, *args, **argitems)
            finally:
                self.lock.release()
            return x

        return _

    def open(self, n=1):
        param = self.dbcf
        newconns = []
        for i in range(0, n):
            try:
                myconn = self.connection_class[param['engine']](param, time.time(), 0)
                newconns.append(myconn)
            except Exception, e:
                print e
                log.error("%s connection error!" % param)
        self.dbconn_idle += newconns

    def clear_timeout(self):
        # log.info('try clear timeout conn ...')
        now = time.time()
        dels = []
        allconn = len(self.dbconn_idle) + len(self.dbconn_using)
        for c in self.dbconn_idle:
            if allconn == 1:
                break
            if now - c.lasttime > 10:
                dels.append(c)
                allconn -= 1

        log.warn('close timeout db conn:%d', len(dels))
        for c in dels:
            c.close()
            self.dbconn_idle.remove(c)

    @synchronize
    def acquire(self, timeout=None):
        try_count = 10
        while len(self.dbconn_idle) == 0:
            try_count -= 1
            if not try_count:
                break
            if len(self.dbconn_idle) + len(self.dbconn_using) < self.max_conn:
                self.open()
                continue
            self.cond.wait(timeout)

        if not self.dbconn_idle:
            return None
        conn = self.dbconn_idle.pop(0)
        conn.useit()
        self.dbconn_using.append(conn)

        if random.randint(0, 100) > 80:
            self.clear_timeout()

        return conn

    @synchronize
    def release(self, conn):
        self.dbconn_using.remove(conn)
        conn.releaseit()
        self.dbconn_idle.insert(0, conn)
        self.cond.notify()

    @synchronize
    def alive(self):
        for conn in self.dbconn_idle:
            conn.alive()

    def size(self):
        return len(self.dbconn_idle), len(self.dbconn_using)


def checkalive(name=None):
    global dbpool
    while True:
        if name is None:
            checknames = dbpool.keys()
        else:
            checknames = [name]
        for k in checknames:
            pool = dbpool[k]
            pool.alive()
        time.sleep(300)


def install(cf, force=False):
    global dbpool
    if dbpool and not force:
        return dbpool
    dbpool = {}
    for name, item in cf.iteritems():
        # item = cf[name]
        dbp = DBPool(item)
        dbpool[name] = dbp
    return dbpool


def acquire(name, timeout=None):
    global dbpool
    # log.info("acquire:", name)
    pool = dbpool.get(name, None)
    x = None
    if pool:
        x = pool.acquire(timeout)
        if x:
            x.name = name
    return x


def release(conn):
    global dbpool
    # log.info("release:", name)
    if not conn:
        return None
    pool = dbpool[conn.name]
    return pool.release(conn)


def execute(db, sql, param=None):
    return db.execute(sql, param)


def executemany(db, sql, param):
    return db.executemany(sql, param)


def query(db, sql, param=None, isdict=True):
    return db.query(sql, param, isdict)


def with_database(name, errfunc=None, errstr=''):
    def f(func):
        def _(self, *args, **argitems):
            self.db = acquire(name)
            x = None
            try:
                x = func(self, *args, **argitems)
            except:
                if errfunc:
                    return getattr(self, errfunc)(error=errstr)
                else:
                    raise
            finally:
                release(self.db)
                self.db = None
            return x

        return _

    return f


def with_database_class(name):
    def _(cls):
        try:
            cls.db = acquire(name)
        except:
            cls.db = None
        finally:
            release(cls.db)
        return cls
    return _
