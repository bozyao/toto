# coding: utf-8
import json
import logging
from datetime import datetime, date

try:
    from conf.settings import database, BASE_DB, settings

    logging.info("Data config by local......")
except ImportError:
    from base.base_conf.settings import database, BASE_DB, settings

    logging.info("Data config by base......")

from base.base_lib.dbpool import with_database_class, install
from base.base_lib import dbpool

if settings.get("debug", False):
    logging.info("Running in debugging mode......")
    dbpool.debug = True

install(database)


def format_date(obj):
    """
        @todo: json dumps时使用的输出格式（暂时先这两个，以后可以加入，如自定义的对象）
        @param obj: 需要转换的对象
        @return: 转换后的样子
    """
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')


# TODO 未考虑redis缓存数据
@with_database_class(BASE_DB)
class BaseModel:
    def __init__(self):
        """
        __table__: 实体表明
        __fields__: 字段
        """
        self.__table__ = ""
        self.__fields__ = "id"
        # 考虑是否加入类型，默认值，范围等？

    def get(self, key, value=""):
        return self.real_dict().get(key, value)

    def set(self, key, value=""):
        self.__dict__[key] = value

    def to_json(self, data=None):
        """输出有意义的属性json格式
        @param data: 要转化的数据，默认为空，使用对象本身
        @return: 属性json格式
        """
        if not data:
            data = self.real_dict()
        return json.dumps(data, default=format_date)

    def real_dict(self):
        """输出有意义的属性字典
        @param:
        @return: 属性字典
        """
        data = self.__dict__.copy()
        for key in data.keys():
            if key.find('__') == 0 or key == 'db':
                data.pop(key)
        return data

    def load(self, json_data):
        """加载数据
        @param json_data: dict数据
        @return: 成功与否
        """
        try:
            cur_keys = self.__fields__.replace(" ", "")
            for key in json_data.keys():
                if key in cur_keys.split(","):
                    self.__dict__[key] = json_data[key]
            return self
        except Exception, e:
            logging.error(e)
            return None

    def save(self):
        """保存自身，新增
        @param:
        @return: 成功与否
        """
        if not self.__table__:
            return 0
        try:
            if self.real_dict().get("id", 0):
                return self.update()
            return self.db.insert(self.__table__, self.real_dict())
        except:
            return 0

    def update(self):
        """更新自身
        @param:
        @return: 成功与否
        """
        if not self.__table__ or not self.real_dict().get("id", 0):
            return 0
        try:
            return self.db.update(self.__table__, self.real_dict(), {"id": self.id})
        except:
            return 0

    def update_values(self, data, where=None):
        """批量更新
        @param data: 要更新的键值对
        @param where: 条件键值对，默认使用自己的id
        @return: 成功与否
        """
        if not self.__table__:
            return 0
        if not where:
            if self.real_dict().get("id", ""):
                where = {"id": self.id}
            else:
                return 0
        ret = 0
        if data:
            ret = self.db.update(self.__table__, data, where)
        return ret

    def delete_by_id(self, id):
        """通过id删除
        @param id: id
        @return: 成功与否
        """
        if not self.__table__:
            return 0
        ret = self.db.delete(self.__table__, {"id": id})
        return ret

    def get_by_id(self, id):
        """通过id获取
        @param id: id
        @return: json数据结构 dict
        """
        if not self.__table__:
            return {}

        ret = self.db.select(self.__table__, {"id": id}, self.__fields__)
        if ret:
            # return self.to_json(ret[0])
            return ret[0]
        return {}

    def select(self, where={}, other='', fields=''):
        """自定义查询
        @param where: dict键值对条件
        @param other: 自定义的
        @param fields: 查询字段
        @return: dict数据结构 数组
        """
        if not self.__table__:
            return []

        if not fields:
            fields = self.__fields__

        data = self.db.select(self.__table__, where, fields, other)
        return data

    def query(self, sql):
        """自定义SQL查询
        @param sql: 直接sql查询
        @return: dict数据结果（不一定和当前model结构对等）
        """
        if not self.__table__:
            return []
        ret = self.db.query(sql)
        return ret

    def execute(self, sql):
        """自定义SQL执行
        @param sql: 直接sql
        @return: 执行结果
        """
        if not self.__table__:
            return []
        ret = self.db.execute(sql)
        return ret

    def escape(self, s):
        return self.db.escape(s)

    def format_json_str_list(self, data=[]):
        ret = []
        for row in data:
            ret.append(self.to_json(row))
        return ret

    def load_info_to_list(self, datas, field="poi_id", info_field="poi"):
        """加载信息到数据集中
        Args:
            datas: 要加工的数据
            field: 源数据中的id字段
            info_field: 要加入的信息对于的key
        Returns:
            加工完的数据
        """
        ids = ",".join([str(data[field]) for data in datas if data[field]])
        if not ids:
            return datas
        infos = self.select(other="where id in (%s)" % ids)
        for info in infos:
            for data in datas:
                if data[field] == info["id"]:
                    data[info_field] = info
        return datas

    def add_count(self, field_name, count=1):
        """ 给int字段加值
        @param field_name: 字段名
        @param count: 加的数量，默认1，可以是负数
        @return: 成功与否
        """
        try:
            sql = "update %s set %s = %s + %d where id = %d" % (
                self.__table__, field_name, field_name, count, self.id
            )
            self.execute(sql)
            return True
        except Exception, e:
            import logging
            logging.error("Add count error, info:%s" % e)
            return False

    def get_count(self, where={}):
        tmp_data = self.select(where, fields="count(id) as count")
        return tmp_data[0]["count"]


if __name__ == "__main__":
    b = BaseModel()
    b.name = "121"
    print b.to_json()
    print b.save()
    print b.__dict__
