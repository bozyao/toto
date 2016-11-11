# coding: utf-8
import tornado.web
import json
import logging
from error_code import ERROR_CODE, ERROR_MSG
from tools.session import Session
from datetime import datetime, date

URL_PREFIX = "/api"


def format_date(obj):
    """json dumps时使用的输出格式（暂时先这两个，以后可以加入，如自定义的对象）
        @param obj: 需要转换的对象
        @return: 转换后的样子
    """
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')


class Application(tornado.web.Application):
    def load_handler_module(self, handler_module, perfix=".*"):
        """从模块加载RequestHandler
        @param handler_module: 模块
        @param perfix: url 前缀
        """
        is_handler = lambda cls: isinstance(cls, type) \
                                 and issubclass(cls, RequestHandler)

        has_pattern = lambda cls: hasattr(cls, 'url_pattern') \
                                  and cls.url_pattern
        handlers = []
        for i in dir(handler_module):
            cls = getattr(handler_module, i)
            if is_handler(cls) and has_pattern(cls):
                handlers.append((cls.url_pattern, cls))
                handlers.append((cls.url_pattern + "/.*", cls))
                logging.info("Load url_pattern: %s" % cls.url_pattern)
        self.add_handlers(perfix, handlers)

    def _get_host_handlers(self, request):
        """覆写父类方法, 一次获取所有可匹配的结果. 父类中该方法一次匹配成功就返回, 忽略后续
            匹配结果. 现通过使用生成器, 如果一次匹配的结果不能使用可以继续匹配.
        @param request: tornado request对象
        """
        host = request.host.lower().split(':')[0]
        handlers = (i for p, h in self.handlers for i in h if p.match(host))
        if not handlers and "X-Real-Ip" not in request.headers:
            handlers = [i for p, h in self.handlers for i in h if p.match(self.default_host)]
        return handlers


class RequestHandler(tornado.web.RequestHandler):
    """覆写tornado的RequestHandler
    使其可以配置url_pattern就可以被加载
    """

    def __init__(self, *argc, **argkw):
        super(RequestHandler, self).__init__(*argc, **argkw)
        self.session = None
        if self.application.use_session:
            self.session = Session(self.application.session_manager, self)

        self.set_header('Content-Type', 'text/json')

        if self.settings.get("debug", False):
            self.access_control_allow()

            # if self.settings['allow_remote_access']:
            #    self.access_control_allow()

    def access_control_allow(self):
        # 允许 JS 跨域调用
        self.set_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Depth, User-Agent, X-File-Size, "
                                                        "X-Requested-With, X-Requested-By, If-Modified-Since, "
                                                        "X-File-Name, Cache-Control, Token")
        self.set_header('Access-Control-Allow-Origin', '*')

    def check_session(self, crypt=False, html=False):
        if self.session:
            return True
        self.set_status(403)
        self.ret_error("VERIFY_FAILED", crypt=crypt)
        return False

    def get(self):
        self.set_status(404)
        self.ret_error("NOT_FOUND", "404")

    def post(self):
        self.set_status(404)
        self.ret_error("NOT_FOUND", "404")

    def delete(self):
        self.set_status(404)
        self.ret_error("NOT_FOUND", "404")

    def put(self):
        self.set_status(404)
        self.ret_error("NOT_FOUND", "404")

    def write(self, chunk):
        if self._finished:
            return
        super(RequestHandler, self).write(chunk)

    # 捕捉未处理的异常,统一处理返回
    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)
        errot_info = ["请求出了点问题，攻城狮正在火速解决~", "SERVER_MAINTENANCE"]
        try:
            tmp_errot_info = kwargs.get("exc_info", ("", ("", "")))[1]
            errot_info[0] = tmp_errot_info.args[0]
            if self.settings.get("debug", False) and len(tmp_errot_info.args) > 1:
                errot_info[0] += ":" + tmp_errot_info.args[1]
        except Exception, e:
            logging.error("Return error error, info:%s" % e)

        logging.error("status:%s error_info:%s" % (status_code, kwargs))
        return self.ret_error(errot_info[1], errot_info[0])

    # 返回json的统一处理,格式统一
    def ret_data(self, data={}, max_age=0):
        if type(data) != dict:
            try:
                data = json.loads(data)
            except Exception, e:
                logging.error("Load json error: %s" % e)
                return self.ret_error("CONTENT_ERROR", "服务器开小差了，攻城狮正在火速解决~")

        if not data.get("error_code", 0):
            data["error_code"] = 0
        if max_age and not self.session:
            self.set_header("Cache-Control", "public max-age=%s" % max_age)

        self.write(json.dumps(data, default=format_date))
        if not self._finished:
            self.finish()
        return

    # 统一错误输出
    def ret_error(self, error_info, msg=ERROR_MSG):
        data = {"error_code": ERROR_CODE.get(error_info, 11111), "msg": msg}
        self.write(json.dumps(data))

        if not self._finished:
            self.finish()
        return


# 路由装饰器
def route(url_pattern=""):
    """路由装饰器, 只能装饰 RequestHandler 子类
    对于没有设置 url_pattern 的Handler，将默认设置url_pattern
    Args:
        url_pattern: 路由解释
    """

    def handler_wapper(cls):
        assert (issubclass(cls, RequestHandler))

        if not url_pattern:
            cls.url_pattern = URL_PREFIX + "/" + str(cls)[8:-9].lower().replace(".", "/").replace("/__init__", "")
        else:
            cls.url_pattern = url_pattern
        return cls

    return handler_wapper


def check_session(permission="login"):
    """检查session信息的装饰器
    Args:
        permission: 权限， 默认login， admin的和业务相关，自行重写，暂时无用
    Returns：
        装饰后的函数（方法）
    """

    def fc(func):
        def _(self, *args, **argitems):

            # TEST
            # return func(self, *args, **argitems)

            if not self.session or not self.session.get("user_id"):
                self.ret_error("VERIFY_FAILED", "需要登录后才可以操作哦")
            else:
                logging.info("User session checked by user_id: %s" % self.session.get("user_id", ""))
                return func(self, *args, **argitems)

        return _

    return fc
