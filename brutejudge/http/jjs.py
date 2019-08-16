import json, base64
from brutejudge.error import BruteError
from brutejudge.http.base import Backend
from brutejudge.http.ejudge import do_http, get, post

def gql_req(url, query, params, headers={}):
    headers = dict(headers)
    headers['Content-Type'] = 'application/json'
    code, headers, data = post(url, json.dumps({"query": query, "variables": params}), headers)
    try: return (code, headers, json.loads(data.decode('utf-8')))
    except json.JSONDecodeError: return (code, headers, None)

def gql_ok(data):
    return data and 'data' in data and 'errors' not in data

class JJS(Backend):
    @staticmethod
    def detect(url):
        sp = url.split('/')
        return sp[0] in ('http:', 'https:') and not sp[1] and sp[2].endswith(':1779')
    def __init__(self, url, login, password):
        Backend.__init__(self)
        url, params = url.split('?')
        if url.endswith('/'): url = url[:-1]
        url += '/graphql'
        params = {k: v for k, v in (i.split('=', 1) if '=' in i else (i, None) for i in params.split('&'))}
        contest_id = params['contest']
        if 'token' in params:
            self.cookie = password
        else:
            code, headers, data = gql_req(url, 'mutation($a:String!,$b:String!){authSimple(login:$a,password:$b){data}}', {"a": login, "b": password})
#           print(url, code, headers, data)
            if not gql_ok(data):
                raise BruteError('Login failed')
            self.cookie = data['data']['authSimple']['data']
        self.url = url
        self.contest = contest_id
    def task_list(self):
        code, headers, data = gql_req(self.url, 'query{contests{id,problems{id}}}', None, {"X-JJS-Auth": self.cookie})
#       print(data)
        if not gql_ok(data):
            raise BruteError("Failed to fetch task list")
        return [j['id'] for i in data['data']['contests'] if i['id'] == self.contest for j in i['problems']]
    def submission_list(self):
        code, headers, data = gql_req(self.url, 'query{submissions{id,problem{id}}}', None, {"X-JJS-Auth": self.cookie})
#       print(data)
        if gql_ok(data):
            return list(reversed([i['id'] for i in data['data']['submissions']])), list(reversed([i['problem']['id'] for i in data['data']['submissions']]))
        return [], []
    def submission_results(self, id):
        return [], []
    def task_ids(self):
        return list(range(len(self.task_list())))
    def submit(self, taskid, lang, text):
        tl = self.task_list()
        if taskid not in range(len(tl)): return
        cl = self.compiler_list(taskid)
        taskid = tl[taskid]
        if lang not in range(len(cl)): return
        lang = cl[lang][1]
        if isinstance(text, str): text = text.encode('utf-8')
        code, headers, data = gql_req(self.url, 'mutation($z:String!,$a:String!,$b:String!,$c:String!){submitSimple(toolchain:$b,runCode:$c,problem:$a,contest:$z){id}}', {'b': lang, 'c': base64.b64encode(text).decode('ascii'), 'a': taskid, 'z': self.contest}, {"X-JJS-Auth": self.cookie})
#       print(code, headers, data)
    def compiler_list(self, task):
        code, headers, data = gql_req(self.url, 'query{toolchains{id,name}}', None, {"X-JJS-Auth": self.cookie})
        if gql_ok(data):
            return [(i, x['id'], x['name']) for i, x in enumerate(data['data']['toolchains'])]
        else:
            raise BruteError("Failed to fetch language list")
    def _submission_descr(self, id):
        id = int(id)
        code, headers, data = gql_req(self.url, 'query{submissions{id,status{code},score}}', None, {"X-JJS-Auth": self.cookie})
        if gql_ok(data):
            for i in data['data']['submissions']:
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
        return ({'score': self.submission_score(id)}, None)
    def submission_score(self, id):
        st = self._submission_descr(id)
#       if isinstance(st, dict) and 'Done' in st:
#           return st['Done'].get('score', None)
#       else: return None
        return st['score'] if st != None else None
