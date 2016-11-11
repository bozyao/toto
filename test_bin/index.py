# coding: utf-8

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if __name__ == "__main__":
    from base.main import run, current_path
    path = current_path()
    logging.info("Start path: %s" % path)
    run(path)
