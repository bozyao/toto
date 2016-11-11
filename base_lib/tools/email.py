#coding: utf-8
__author__ = 'yaobo'


def check_format(email):
    import re
    ret = re.findall('^[^@]{2,}@[\w\d]{2,}\.[\w]{2,}$', email)
    return ret

if __name__ == "__main__":
    print check_format("afbd@dd")
    print check_format("sdnv@dd.co")