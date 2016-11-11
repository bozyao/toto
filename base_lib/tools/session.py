# coding: utf-8
__author__ = 'bozyao'

import uuid
import hmac
import json
import hashlib
import redis


class SessionData(dict):
    def __init__(self, session_id, hmac_key):
        self.session_id = session_id
        self.hmac_key = hmac_key


class Session(SessionData):
    def __init__(self, session_manager, request_handler):
        self.session_manager = session_manager
        self.request_handler = request_handler
        try:
            current_session = session_manager.get(request_handler)
        except InvalidSessionException:
            current_session = session_manager.get()
        for key, data in current_session.iteritems():
            self[key] = data
        self.session_id = current_session.session_id
        self.hmac_key = current_session.hmac_key

    def save(self):
        self.session_manager.set(self.request_handler, self)

    def remove(self):
        self.session_manager.remove(self)

    def get_all(self):
        return self.session_manager.get_all()


class SessionManager(object):
    def __init__(self, secret, store_options, session_timeout, m_db=None):
        self.secret = secret
        self.session_timeout = session_timeout
        self.m_db = m_db
        try:
            self.redis = redis.StrictRedis(host=store_options['redis_host'],
                                           port=store_options['redis_port'],
                                           db=store_options['redis_db'])
        except Exception as e:
            print e

    def _fetch(self, session_id):
        try:
            session_data = raw_data = self.redis.get(session_id)
            if not raw_data:
                session_data = raw_data = self.get_m_db_data(session_id)

            if raw_data != None:
                # self.redis.set(session_id, raw_data)
                self.redis.setex(session_id, self.session_timeout, raw_data)
                try:
                    session_data = json.loads(raw_data)
                except:
                    session_data = {}
            if type(session_data) == type({}):
                return session_data
            else:
                return {}
        except IOError:
            return {}

    def get_session_id(self, request_handler):

        session_id = ""
        if not request_handler.get_argument("sid", ""):
            t_session_id = request_handler.get_cookie("session_id")
            session_id = request_handler.get_cookie("sid")
            if not t_session_id and session_id and len(session_id) == 64:
                pass
            else:
                session_id = request_handler.get_secure_cookie("session_id")
        else:
            session_id = request_handler.get_argument("sid", "")

        return session_id

    def get(self, request_handler=None):
        if (request_handler == None):
            session_id = None
            hmac_key = None
        else:
            session_id = self.get_session_id(request_handler)
            # request_handler.get_secure_cookie("session_id")
            hmac_key = request_handler.get_secure_cookie("verification")
        if not session_id:
            session_exists = False
            session_id = self._generate_id()
            hmac_key = self._generate_hmac(session_id)
        else:
            session_exists = True
        '''check_hmac = self._generate_hmac(session_id)
        if hmac_key != check_hmac:
            raise InvalidSessionException()'''
        session = SessionData(session_id, hmac_key)
        if session_exists:
            session_data = self._fetch(session_id)
            for key, data in session_data.iteritems():
                session[key] = data
        return session

    def set(self, request_handler, session):
        request_handler.set_secure_cookie("session_id", session.session_id)
        # request_handler.set_secure_cookie("verification", session.hmac_key)
        session_data = json.dumps(dict(session.items()))
        # self.redis.set(session.session_id, session_data)
        self.set_m_db_data(session.session_id, session_data)
        self.redis.setex(session.session_id, self.session_timeout, session_data)

    def remove(self, session):
        self.rm_m_db_data(session.session_id)
        self.redis.delete(session.session_id)

    def get_all(self):
        return len(self.redis.keys())

    def _generate_id(self):
        new_id = hashlib.sha256(self.secret + str(uuid.uuid4()))
        return new_id.hexdigest()

    def _generate_hmac(self, session_id):
        return hmac.new(session_id, self.secret, hashlib.sha256).hexdigest()

    def set_m_db_data(self, k, v):
        if not self.m_db:
            return 0
        if not v:
            return 0
        #data = self.m_db.get("select * from user_session where sid = '%s'" % k)
        data = self.get_m_db_data(k)
        if data:
            flag = self.m_db.execute("update user_session set vl = '%s' where sid = '%s'" % (v, k))
        else:
            flag = self.m_db.insert("user_session", {
                "sid": k,
                "vl": v
            })
        return flag

    def get_m_db_data(self, k):
        if not self.m_db:
            return None
        sql = "select vl from user_session where sid = '%s'" % k
        data = self.m_db.get(sql)
        if data:
            data = data["vl"]
        return data

    def rm_m_db_data(self, k):
        if not self.m_db:
            return 0
        return self.m_db.execute("delete from user_session where sid='%s'" % k)


class InvalidSessionException(Exception):
    pass
