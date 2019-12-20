import json, base64, socket
from brutejudge.error import BruteError
from brutejudge._http.base import Backend
from brutejudge._http.ejudge import do_http, get, post

def gql_req(url, query, params, headers={}):
    headers = dict(headers)
    for k, v in list(headers.items()):
        if v == None: del headers[k]
    headers['Content-Type'] = 'application/json'
    code, headers, data = post(url, json.dumps({"query": query, "variables": params}), headers)
    try: return (code, headers, json.loads(data.decode('utf-8')))
    except json.JSONDecodeError:
#       print(data)
        return (code, headers, None)

def gql_ok(data):
    return data and 'data' in data and 'errors' not in data

class JJS(Backend):
    @staticmethod
    def detect(url):
        sp = url.split('/')
        return sp[0] in ('http+jjs:', 'https+jjs:') and not sp[1]
    @staticmethod
    def login_type(url):
        url, params = url.split('?')
        params = {k: v for k, v in (i.split('=', 1) if '=' in i else (i, None) for i in params.split('&'))}
        if params.get('auth', None) == 'token':
            return ['pass']
        elif params.get('auth', None) in ('gettoken', 'guest'):
            return []
        else:
            return ['login', 'pass']
    def __init__(self, url, login, password):
        Backend.__init__(self)
        url, params = url.split('?')
        url = url.replace('+jjs', '', 1)
        if url.endswith('/'): url = url[:-1]
        url += '/graphql'
        params = {k: v for k, v in (i.split('=', 1) if '=' in i else (i, None) for i in params.split('&'))}
        contest_id = params['contest']
        if params.get('auth', None) == 'token':
            self.cookie = password
        elif params.get('auth', None) == 'gettoken':
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect('/tmp/jjs-auth-sock')
            token = b''
            while True:
                chk = sock.recv(1024)
                token += chk
                if not chk: break
            token = token.decode('ascii').strip()
            if not (token.startswith('===') and token.endswith('===')):
                raise BruteError('Login failed: failed to get token from jjs-auth-sock')
            self.cookie = token[3:-3]
        elif params.get('auth', None) == 'guest':
            self.cookie = 'Guest'
        else:
            code, headers, data = gql_req(url, 'mutation($a:String!,$b:String!){authSimple(login:$a,password:$b){data}}', {"a": login, "b": password})
#           print(url, code, headers, data)
            if not gql_ok(data):
                if 'errors' in data and len(data['errors']) == 1 and 'extensions' in data['errors'][0] and 'errorCode' in data['errors'][0]['extensions']:
                    raise BruteError('Login failed: '+data['errors'][0]['extensions']['errorCode'])
                raise BruteError('Login failed')
            self.cookie = data['data']['authSimple']['data']
        self.url = url
        self.contest = contest_id
        self.lsu_cache = {}
    def task_list(self):
        code, headers, data = gql_req(self.url, 'query{contests{id,problems{id}}}', None, {"X-Jjs-Auth": self.cookie})
#       print(data)
        if not gql_ok(data):
            raise BruteError("Failed to fetch task list")
        return [j['id'] for i in data['data']['contests'] if i['id'] == self.contest for j in i['problems']]
    def submission_list(self):
        code, headers, data = gql_req(self.url, 'query{runs{id,problem{id}}}', None, {"X-Jjs-Auth": self.cookie})
#       print(data)
        if gql_ok(data):
            return list(reversed([i['id'] for i in data['data']['runs']])), list(reversed([i['problem']['id'] for i in data['data']['runs']]))
        return [], []
    def submission_results(self, id):
        code, headers, data = gql_req(self.url, 'query($a:Int!){runs(id:$a){invocationProtocol(filter:{compileLog:false,testData:false,output:false,answer:false})}}', {"a": int(id)}, {"X-Jjs-Auth": self.cookie})
#       print(code, headers, data)
        if not gql_ok(data) or len(data['data']['runs']) != 1:
#           raise BruteError("Failed to fetch testing protocol")
            return [], []
        prot = json.loads(data['data']['runs'][0]['invocationProtocol'])
        return [self._format_status(i['status_code']) for i in prot['tests']], ['?.???' for i in prot['tests']]
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
        code, headers, data = gql_req(self.url, 'mutation($z:String!,$a:String!,$b:String!,$c:String!){submitSimple(toolchain:$b,runCode:$c,problem:$a,contest:$z){id}}', {'b': lang, 'c': base64.b64encode(text).decode('ascii'), 'a': taskid, 'z': self.contest}, {"X-Jjs-Auth": self.cookie})
#       print(code, headers, data)
    def compiler_list(self, task):
        code, headers, data = gql_req(self.url, 'query{toolchains{id,name}}', None, {"X-Jjs-Auth": self.cookie})
        if gql_ok(data):
            return [(i, x['id'], x['name']) for i, x in enumerate(data['data']['toolchains'])]
        else:
            raise BruteError("Failed to fetch language list")
    def _submission_descr(self, id):
        id = int(id)
        code, headers, data = gql_req(self.url, 'query{runs{id,status{code},score,liveStatusUpdate{liveScore,currentTest,finish}}}', None, {"X-Jjs-Auth": self.cookie})
        if gql_ok(data):
            for i in data['data']['runs']:
                if i['id'] == id:
#                   print(i)
                    return i
        return None
    def _get_lsu(self, id, lsu):
        id = int(id)
        if lsu['finish']:
            try: del self.lsu_cache[id]
            except KeyError: pass
            return None
        if id not in self.lsu_cache: self.lsu_cache[id] = {'test': None, 'score': None}
        if lsu['currentTest'] != None: self.lsu_cache[id]['test'] = lsu['currentTest']
        if lsu['liveScore'] != None: self.lsu_cache[id]['score'] = lsu['liveScore']
        return self.lsu_cache[id]
    def _format_status(self, st):
        st = st.replace('_', ' ')
        if st == 'ACCEPTED' or st == 'TEST PASSED': return 'OK'
        return st[:1].upper()+st[1:].lower()
    def compile_error(self, id, *, binary=False, kind=None):
        if kind in (None, 1):
            code, headers, data = gql_req(self.url, 'query($a:Int!){runs(id:$a){invocationProtocol(filter:{compileLog:true,testData:false,output:false,answer:false})}}', {"a": int(id)}, {"X-Jjs-Auth": self.cookie})
            if not gql_ok(data) or len(data['data']['runs']) != 1: return None
            prot = json.loads(data['data']['runs'][0]['invocationProtocol'])        
            ans = base64.b64decode(prot.get('compile_stdout', '').encode('ascii'))+base64.b64decode(prot.get('compile_stderr', '').encode('ascii'))
        elif kind == 3:
            code, headers, data = gql_req(self.url, 'query($a:Int!){runs(id:$a){binary}}', {"a": int(id)}, {"X-Jjs-Auth": self.cookie})
            if not gql_ok(data) or len(data['data']['runs']) != 1: return None
            ans = base64.b64decode(data['data']['runs'][0]['binary'].encode('ascii'))
        else: return None
        if not binary: ans = ans.decode('utf-8', 'replace')
        return ans
    def submission_status(self, id):
        st = self._submission_descr(id)
        if st == None: return None
        lsu = self._get_lsu(id, st['liveStatusUpdate'])
        if lsu != None:
            status = 'Running'
            if lsu['test'] != None: status += ', test '+str(lsu['test'])
            return status
        return self._format_status(st['status']['code'])
#       if isinstance(st, str): return st
#       elif isinstance(st, dict) and 'Done' in st:
#          return st['Done'].get('status_name', None)
#       else: return None
    def submission_source(self, id):
        code, headers, data = gql_req(self.url, 'query($a:Int!){runs(id:$a){source}}', {"a": int(id)}, {"X-Jjs-Auth": self.cookie})
        if not gql_ok(data) or len(data['data']['runs']) != 1: return None
        ans = base64.b64decode(data['data']['runs'][0]['source'].encode('ascii'))
        return ans
    def submission_stats(self, id):
        st = self._submission_descr(id)
        if st == None: return None
        lsu = self._get_lsu(id, st['liveStatusUpdate'])
        if lsu != None:
            ans = {'score': lsu['score']}
            if lsu['test'] != None: ans['tests'] = {'success': lsu['test']}
            return (ans, None)
        return ({'score': st['score']}, None)
    def submission_score(self, id):
        st = self._submission_descr(id)
        if st == None: return None
        lsu = self._get_lsu(id)
        if lsu != None: return lsu['score']
#       if isinstance(st, dict) and 'Done' in st:
#           return st['Done'].get('score', None)
#       else: return None
        return st['score']
    def get_samples(self, id, *, binary=False):
        def deb64(x):
            ans = base64.b64decode(x.encode('ascii'))
            if not binary: ans = ans.decode('utf-8', 'replace')
            return ans
        ans = {}
        code, headers, data = gql_req(self.url, 'query($a:Int!){runs(id:$a){invocationProtocol(filter:{compileLog:false,testData:true,output:true,answer:true})}}', {"a": int(id)}, {"X-Jjs-Auth": self.cookie})
        if not gql_ok(data) or len(data['data']['runs']) != 1: return ans
        proto = json.loads(data['data']['runs'][0]['invocationProtocol'])
        for i, j in enumerate(proto['tests']):
            cur = ans[i + 1] = {}
            for k1, k2 in (('test_stdin', 'Input'), ('test_stdout', 'Output'), ('test_stderr', 'Stderr'), ('test_answer', 'Correct')):
                if k1 in j and j[k1] != None: cur[k2] = deb64(j[k1])
        return ans
    def scoreboard(self):
        code, headers, data = gql_req(self.url, 'query{standingsSimple}', None, {"X-Jjs-Auth": self.cookie})
        if not gql_ok(data): return []
        standings = json.loads(data['data']['standingsSimple'])
        ans = []
        i = 1
        while str(i) in standings['parties']:
            cur = standings['parties'][str(i)]
            i += 1
            ans.append(({'name': 'STUB', 'color': cur['stats']['color'], 'total_score': cur['stats']['score']}, []))
            j = 1
            while str(j) in cur['problems']:
                cur2 = cur['problems'][str(j)]
                j += 1
                if cur2['empty']: ans[-1][1].append(None)
                else:
                    ans[-1][1].append({'score': cur2['score'], 'attempts': cur2['attempts'] * (1 if cur2['ok'] else -1)})
        return ans
    def clars(self): return []
