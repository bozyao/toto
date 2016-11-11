from base.base_lib.app_route import route, RequestHandler


@route()
class TestHandler(RequestHandler):
    def get(self):
        self.ret_data(
                {"data": []}
        )


@route()
class WorldHandler(RequestHandler):
    def get(self):
        self.ret_data(
                {"msg": "Say 'Hello world!'"}
        )
