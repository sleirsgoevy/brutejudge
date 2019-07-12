import json, base64
from brutejudge.error import BruteError
from brutejudge.http.base import Backend
from brutejudge.http.ejudge import do_http, get, post

def json_req(url, data, headers={}):
    headers = dict(headers)
    headers['Content-Type'] = 'application/json'
    if data != None: code, headers, data = post(url, json.dumps(data), headers)
    else: code, headers, data = get(url, headers)
    try: return (code, headers, json.loads(data.decode('utf-8')))
    except json.JSONDecodeError: return (code, headers, None)

class JJS(Backend):
    @staticmethod
    def detect(url):
        sp = url.split('/')
        return sp[0] in ('http:', 'https:') and not sp[1] and sp[2].endswith(':1779')
    def __init__(self, url, login, password):
        Backend.__init__(self)
        url, params = url.split('?')
        params = {k: v for k, v in (i.split('=', 1) if '=' in i else (i, None) for i in params.split('&'))}
        contest_id = params['contest']
        if 'token' in params:
            self.cookie = password
        else:
            code, headers, data = json_req(url+'/auth/simple', {"login": login, "password": password})
#           print(url, code, headers, data)
            if not data or 'Ok' not in data:
                raise BruteError('Login failed')
            self.cookie = data['Ok']['buf']
        self.url = url
        self.contest = contest_id
    def _task_list(self):
        code, headers, data = json_req(self.url+'/contests/describe', self.contest, {"X-JJS-Auth": self.cookie})
#       print(data)
        if not data or 'Ok' not in data:
            raise BruteError('Login failed')
        return [(i['code'], 'todo') for i in data['Ok']['problems']]
    def task_list(self):
        return [i[0] for i in self._task_list()]
    def submission_list(self):
        code, headers, data = json_req(self.url+"/submissions/list", {'limit': 2147483647}, {"X-JJS-Auth": self.cookie})
        tl = {j:i for i, j in self._task_list()}
#       print(data)
        if data and 'Ok' in data:
            return list(reversed([i['id'] for i in data['Ok']])), list(reversed(['dummy' for i in range(len(data['Ok']))]))
        return [], []
    def submission_results(self, id):
        return [], []
    def task_ids(self):
        return list(range(len(self.task_list())))
    def submit(self, taskid, lang, text):
        if isinstance(text, str): text = text.encode('utf-8')
        code, headers, data = json_req(self.url+"/submissions/send", {'toolchain': lang, 'code': base64.b64encode(text).decode('ascii'), 'problem': self.task_list()[taskid], 'contest': self.contest}, {"X-JJS-Auth": self.cookie})
#       print(code, headers, data)
    def compiler_list(self, task):
        code, headers, data = json_req(self.url+"/toolchains/list", {}, {"X-JJS-Auth": self.cookie})
        if data and 'Ok' in data:
            return [(x['id'], x['name'], x['name']) for x in data['Ok']]
        else:
            raise BruteError("Failed to fetch language list")
    def _submission_descr(self, id):
        code, headers, data = json_req(self.url+"/submissions/list", {'limit': 2147483647}, {"X-JJS-Auth": self.cookie})
        if data and 'Ok' in data:
            for i in data['Ok']:
                if i['id'] == id:
                    return i
        return None
    def submission_status(self, id):
        st = self._submission_descr(id)
#       if isinstance(st, str): return st
#       elif isinstance(st, dict) and 'Done' in st:
#          return st['Done'].get('status_name', None)
#       else: return None
        if st == None: return None
        st = st['status']['code'].replace('_', ' ')
        if st == 'ACCEPTED': return 'OK'
        return st[:1].upper()+st[1:].lower()
    def compile_error(self, id):
        return 'STUB'
    def submission_stats(self, id):
        return ({}, None)
    def submission_score(self, id):
        st = self._submission_descr(id)
#       if isinstance(st, dict) and 'Done' in st:
#           return st['Done'].get('score', None)
#       else: return None
        return st['score'] if st != None else None
