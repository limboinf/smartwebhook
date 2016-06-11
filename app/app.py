# coding=utf-8
"""
webhook
    :copyright: (c) 2016 by fangpeng(@beginman.cn).
    :license: MIT, see LICENSE for more details.
"""
import json
import os
import subprocess
from bottle import Bottle, get, post, run, request

base = os.path.dirname(__file__)
project_file = os.path.join(base, 'projects.json')

app = Bottle()


@app.post('/')
def index():
    data = dict(request.forms)
    print '-----------\n', data
    print dict(request.headers)
    return {"hello": "world"}


@app.post('/push/<project>')
def push(project):
    with open(project_file, 'r') as fb:
        projects = json.load(fb)
        if project not in projects:
            raise ValueError("project dose not exist!")

        item = projects[project]
        p = subprocess.Popen('cd ' + item['path'] + ';ls', shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        m = subprocess.Popen(item['command'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in m.stdout.readlines():
            print line

        retval = p.wait()
        data = dict(request.forms)
        # todo: check request header
        # todo: vaild request
        print dict(request.headers)
        return data

run(app, host="0.0.0.0", port=7777, debug=True)