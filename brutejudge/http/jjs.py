import json
from brutejudge.error import BruteError
from brutejudge.http.ejudge import do_http, get, post

def json_req(url, data, headers={}):
    headers = dict(headers)
    headers['Content-Type'] = 'application/json'
    if data != None: code, headers, data = post(url, json.dumps(data), headers)
    else: code, headers, data = get(url, headers)
    try: return (code, headers, json.loads(data.decode('utf-8')))
    except json.JSONDecodeError: return (code, headers, None)

class JJS:
    @staticmethod
    def detect(url):
        sp = url.split('/')
        return sp[0] in ('http:', 'https:') and not sp[1] and sp[2].endswith(':1779')
    def __init__(self, url, login, password):
        code, headers, data = json_req(url+'/auth/simple', {"login": login, "password": password})
#       print(url, code, headers, data)
        if not data or 'Ok' not in data:
            raise BruteError('Login failed')
        self.url = url
        self.cookie = data['Ok']['buf']
    def task_list(self):
        return ['dummy']
    def submission_list(self):
        code, headers, data = json_req(self.url+"/submissions/list?limit=2147483647", None, {"X-JJS-Auth": self.cookie})
        if data and 'Ok' in data:
            return list(reversed([i['id'] for i in data['Ok']])), ['dummy' for i in range(len(data['Ok']))]
        return [], []
    def submission_results(self, id):
        return [], []
    def task_ids(self):
        return [0]
    def submit(self, taskid, lang, text):
        if isinstance(text, str): text = text.encode('utf-8')
        code, headers, data = json_req(self.url+"/submission/send", {'toolchain': lang, 'code': list(text)}, {"X-JJS-Auth": self.cookie})
#       print(code, headers, data)
    def compiler_list(self, task):
        code, headers, data = json_req(self.url+"/toolchains/list", None, {"X-JJS-Auth": self.cookie})
        if data and 'Ok' in data:
            return [(x['id'], x['name'], x['name']) for x in data['Ok']]
        else:
            raise BruteError("Failed to fetch language list")
    def _submission_descr(self, id):
        code, headers, data = json_req(self.url+"/submissions/list?limit=2147483647", None, {"X-JJS-Auth": self.cookie})
        if data and 'Ok' in data:
            for i in data['Ok']:
                if i['id'] == id:
                    return i['state']
        return None
    def submission_status(self, id):
        st = self._submission_descr(id)
        if isinstance(st, str): return st
        elif isinstance(st, dict) and 'Done' in st:
           return st['Done'].get('status_name', None)
        else: return None
    def compile_error(self, id):
        return 'STUB'
    def submission_stats(self, id):
        return ({}, None)
    def submission_score(self, id):
        st = self._submission_descr(id)
        if isinstance(st, dict) and 'Done' in st:
            return st['Done'].get('score', None)
        else: return None
