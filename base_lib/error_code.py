# coding: utf-8
# ==================
# 错误信息及code列表

ERROR_MSG = "服务器链接失败，请稍候再试。"
ERROR_CODE = {
    # 返回内容错误
    "CONTENT_ERROR": 10000,
    "SERVER_MAINTENANCE": 10001,

    # 协议层错误
    "NOT_FOUND": 11000,

    # 第三方或者其他服务错误
    "MYSQL_ERROR": 20001,
    "REDIS_ERROR": 20002,

    # 参数错误
    "ARGUMENT_ERROR": 30001,
    "ALREADY_BUY": 30002,

    # 未知错误
    "UNKNOW_ERROR": 11111,

    # 非法词
    "ILLEGAL_WORD": 40001,
    # 被禁言
    "USER_IS_MUTE": 40002,
    # 重复的发言
    "REPEAT_SEND": 40003,

    # 升级提示
    "UPDATE_ALTER": 50000,

    # User 相关
    "SESSION_IS_NULL": 60000,
    "SESSION_DATA_ERROR": 60001,
    "LIMITED_ACCESS": 60002,
    "PASSWD_IS_NULL": 60003,
    "NAME_CANT_USE": 60004,
    "NAME_IS_EXIST": 60005,
    # refer
    "USER_BIND_ERROR_IS_SELF": 61001,
    "USER_BIND_ERROR_NO_REFERER": 61002,
    "USER_BIND_BOUND": 61003,
    # exchange_code
    "EXCHANGED_PAY_ERROR": 62001,
    # RMB
    "RMB_LACK": 63000,
    # CAIBI
    "CAIBI_CHANGE_ERROR": 68000,

    # 验证失败
    "VERIFY_FAILED": 70000,
    "PHONE_FORMAT_ERROR": 71001,
    "SEND_SMS_ERROR": 72001,
    "CHECK_SMS_ERROR": 72002,
    "T_VERIFY_ERROR": 73001,

    # 交易支付相关
    "HAS_PAY": 80000,

    # prediction
    "NO_STAT_DATA": 90001

}
