# coding: utf-8
import sys
import os
import socket
import importlib
import tornado.ioloop
import tornado.web
import tornado.httpserver
from tornado.options import define, options
import logging
from base_lib.app_route import Application, RequestHandler, URL_PREFIX

socket.setdefaulttimeout(10)
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)

try:
    print "Load local setting..."
    new_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if new_path not in sys.path:
        sys.path.append(new_path)

    from conf.settings import settings, LOAD_MODULE, REJECT_MODULE
except ImportError, e:
    print e
    print "Load local setting error, load base settings..."

    from base.base_conf.settings import settings, LOAD_MODULE, REJECT_MODULE


def current_path():
    path = os.path.realpath(sys.path[0])
    if os.path.isfile(path):
        path = os.path.dirname(path)
        return os.path.abspath(path)
    else:
        import inspect
        caller_file = inspect.stack()[1][1]
        return os.path.abspath(os.path.dirname(caller_file))


# 加载所有handler模块
def load_module(app, path):
    logging.info("Load module path:%s" % path)
    all_py = scan_dir(path)
    # 循环获取所有py文件
    for file_name in all_py:
        i = file_name.replace(path, "")
        mn = i[1:-3].replace("/", ".").replace("\\", ".")
        m = importlib.import_module(mn)

        # 获取有效的Handler类，方法名称
        # 此处如果类名不是Handler结尾，会对自动生成url规则产生影响，暂限定
        hd = [j for j in dir(m) if j[-7:] == "Handler" and j != 'RequestHandler' and j != 'Handler']
        if hd:
            if ((LOAD_MODULE and i in LOAD_MODULE) or not LOAD_MODULE) and i not in REJECT_MODULE:
                logging.info("Load handler file: %s" % file_name)
                app.load_handler_module(m)
            else:
                logging.info("Miss handler file: %s" % file_name)
    return app


# 扫描目录，得到所有py文件
def scan_dir(path, hfs=[]):
    fds = os.listdir(path)
    for i in fds:
        i = os.path.join(path, i)
        if i[-3:] == ".py":
            hfs.append(i)
        elif os.path.isdir(i):
            hfs = scan_dir(i, hfs)
    return hfs


def config_tornado_log(options):
    # 配置tornado日志格式，使用TimedRotating的方式来按天切割日志
    import logging
    from tornado.log import LogFormatter
    if options is None:
        from tornado.options import options

    if options.logging is None or options.logging.lower() == 'none':
        return
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, options.logging.upper()))
    if options.log_file_prefix:
        print "Set logging config with file at %s" % options.log_file_prefix
        channel = logging.handlers.TimedRotatingFileHandler(
                filename=options.log_file_prefix,
                when='midnight',
                interval=1,
                backupCount=10)
        channel.setFormatter(LogFormatter(color=False))
        logger.addHandler(channel)

    if (options.log_to_stderr or
            (options.log_to_stderr is None and not logger.handlers)):
        channel = logging.StreamHandler()
        channel.setFormatter(LogFormatter())
        logger.addHandler(channel)
        logging.info("Set logging config with stdout.")


def run(path="", port=8800, url_prefix=URL_PREFIX, use_session=True):
    import base_lib.app_route
    base_lib.app_route.URL_PREFIX = url_prefix
    define("port", default=port, help="run on the given port", type=int)
    application = Application(None, **settings)
    tornado.options.parse_command_line(final=True)

    if not path:
        path = current_path()
    load_module(application, path)

    http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
    from base_lib.tools import session
    from base_lib.dbpool import acquire

    if use_session:
        sessiion_db = settings.get("session_db", "")
        application.session_manager = session.SessionManager(
                settings["session_secret"],
                settings["store_options"],
                settings["session_timeout"],
                m_db=acquire(sessiion_db)
        )

    application.use_session = use_session
    http_server.listen(options.port)
    logging.info('Server start , port: %s' % options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    run()
