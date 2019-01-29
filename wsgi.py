#!/usr/bin/env python3
import sys
sys.path.append('/var/vk-bots/')
from currency import flask_server
application = flask_server.app

if __name__=='__main__':
    application.run(host='0.0.0.0', debug=True)
