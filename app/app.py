# coding=utf-8
"""
webhook
    :copyright: (c) 2016 by fangpeng(@beginman.cn).
    :license: MIT, see LICENSE for more details.
"""
import json
import threading
import os
import subprocess
from bottle import Bottle, run, request

base = os.path.dirname(__file__)
project_file = os.path.join(base, 'projects.json')
app = Bottle()


@app.post('/push/<project_name>')
def push(project_name):
    msg = 'prepare pulling for project: [%s]....\n' % project_name
    pull_status = '[Fail]'
    is_send_mail = True
    project_info = {}
    try:
        with open(project_file, 'r') as fb:
            projects = json.load(fb)
            if project_name not in projects:
                raise ValueError("project dose not exist!")

            data = dict(request.forms)
            headers = dict(request.headers)
            project_info = projects[project_name]

            # valid request headers
            git_platform = valid_request_headers(headers, project_info)
            if isinstance(git_platform, basestring):    # ping request
                is_send_mail = False
            else:                                       # push request
                platform = git_platform.keys()[0]
                if platform == 'coding':
                    result = handel_coding(data, project_info)
                    is_send_mail = result['pull']
                    stdout_msg = result['msg']
                    is_pull_succeeded = result['is_pull_succeeded']
                    if is_send_mail:
                        if is_pull_succeeded:
                            pull_status = '[OK]'

                        msg += stdout_msg

    except Exception, e:
        # send mail
        msg += str(e)
        print e

    finally:
        if is_send_mail:
            mail = project_info.get('mail', None)
            if mail:
                t = HookThread(send_mail, (msg, project_name, pull_status, mail))
                t.setDaemon(True)
                t.start()
            # send_mail(msg, project_name, pull_status, mail)

        return {}


def valid_request_headers(headers, project_info):
    git = project_info['git']
    for k, v in git.items():
        if not headers['User-Agent'].startswith(v['User-Agent']):
            raise ValueError("Invalid User-Agent:%s" % headers['User-Agent'])

        if headers['X-Coding-Event'] != v['X-Coding-Event']:
            if headers['X-Coding-Event'] == 'ping':
                return 'ping'

            raise ValueError("Invalid User-Agent, excepted X-Coding-Event:%s but got %s" \
                      % (v['X-Coding-Event'], headers['X-Coding-Event']))

        for item_k in v:
            if item_k not in headers:
                raise ValueError("request headers missed key:%s " % item_k)

        return {k: v}

    raise ValueError("Invalid User-Agent")


def send_mail(text, project, status, mail_info):
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(text, 'plain', 'utf-8')
    msg['Subject'] = '%s pull %s' % (project, status)
    msg['From'] = "SmartWebHook"
    try:
        s = smtplib.SMTP()
        s.connect(mail_info['mail_host'], mail_info['mail_port'])
        s.login(mail_info['mail_user'], mail_info['mail_pass'])
        s.sendmail(mail_info['mail_sender'], mail_info['receivers'], msg.as_string())
    except smtplib.SMTPException as ex:
        print "error: send mail failed, ", ex


def handel_coding(data, project_info):
    try:
        data = data.keys()[0]

        if isinstance(data, (basestring,)):
            data = json.loads(data)

        if data.get('event', '') != 'push':
            raise ValueError("Only support push event")

        # valid token
        valid_token(data, project_info)

        # check short message whether is equal to value of the `pull_flag` flag.
        # running command when it's true or it's none.
        commits = data['commits'][0]
        pull_flag = project_info['pull_flag']
        project_path = project_info['path']
        command = 'cd %s;/bin/bash %s' % (project_path, project_info['command'])
        print command
        after_commit_id = data['after']
        is_pull = False
        if pull_flag:
            if commits['short_message'].startswith(pull_flag):
                is_pull = True
        else:
            is_pull = True

        stdout = ''
        if is_pull:
            stdout = run_command(command)
            command = 'cd %s; %s' % (project_path, "git log -n 1 --pretty=oneline")
            print command
            is_pull_succeeded = valid_pull_status(command, after_commit_id)
            if is_pull_succeeded:
                stdout = "[OK] Pull Succeeded!\n" + stdout
            else:
                stdout = "[Fail] Pull Failed!\n" + stdout
            return {'pull': True, 'msg': stdout, 'is_pull_succeeded': is_pull_succeeded}

        return {'pull': False, 'msg': stdout}

    except Exception as ex:
        raise Exception(ex)


def valid_token(data, project_info):
    if 'token' not in data:
        raise ValueError("Missing Token")

    if project_info['token'] != data['token']:
        raise ValueError("Invalid Token")


def run_command(command):
    m = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = ''
    for line in m.stdout.readlines():
        stdout += (line +'\n')
    return stdout


def valid_pull_status(command, after_commit_id):
    m = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    msg = m.stdout.readlines()[0]
    last_commit_id = msg.split(' ')[0]
    return after_commit_id == last_commit_id


class HookThread(threading.Thread):
    def __init__(self, func, args):
        threading.Thread.__init__(self)
        self.func = func
        self.args = args

    def run(self):
        apply(self.func, self.args)

run(app, host="0.0.0.0", port=7777, debug=True)