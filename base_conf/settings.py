# coding: utf-8

import os, sys
import socket

MACHINE_NAME = socket.gethostname()


def current_path():
    path = os.path.realpath(sys.path[0])
    if os.path.isfile(path):
        path = os.path.dirname(path)
        return os.path.abspath(path)
    else:
        import inspect
        caller_file = inspect.stack()[1][1]
        return os.path.abspath(os.path.dirname(caller_file))

ROOT_PATH = os.path.dirname(os.path.dirname(current_path()))

# 只加载某几个模块，为空则全部加载
LOAD_MODULE = []

# 不加载哪几个模块
REJECT_MODULE = []

BUSINESS_REDIS_DB_PARAM = {
    "host": "localhost",
    "port": 6379
}

# =================
# tornado资源配置
settings = {
    "cookie_secret": "e446976943b4e8442f099fed1f3fea28462d5832f483a0ed9a3d5d3859f==08d",
    "session_secret": "3cdcb1f00803b6e78ab50b466a40b9977db396840c28307f428b25e2277f0bcc",
    "session_timeout": 60 * 30 * 2 * 24 * 30,
    "store_options": {
        'redis_host': BUSINESS_REDIS_DB_PARAM["host"],
        'redis_port': BUSINESS_REDIS_DB_PARAM["port"],
        'redis_db': '4',
    },
    "static_path": os.path.join(ROOT_PATH, "static"),
    "template_path": os.path.join(ROOT_PATH, "templates"),
    "gzip": True,
    "debug": False,
}

# =================
# 数据库连接装载

database = {
    'test': {
        'engine': 'mysql',
        'db': 'db_name',
        'host': 'localhost',
        'port': 3306,
        'user': 'bozyao',
        'passwd': 'bozyao',
        'charset': 'utf8mb4',
        'conn': 20
    }
}

BASE_DB = "test"
