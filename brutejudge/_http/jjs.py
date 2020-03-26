import json, base64, socket, urllib.parse
from brutejudge.error import BruteError
from brutejudge._http.base import Backend
from brutejudge._http.ejudge import do_http, get, post

def urlescape(s):
    return urllib.parse.urlencode({'x': s})[2:]

def json_req(url, data, headers={}, method=None):
    print(url)
    if data != None:
        data = json.dumps(data).encode('utf-8')
        if method == None: method = 'POST'
    else:
        data = b''
        if method == None: method = 'GET'
    code, headers, data = do_http(url, method, headers, data)
    try: data = json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError): data = None
    return (code, headers, data)

class JJS(Backend):
    @staticmethod
    def detect(url):
        sp = url.split('/')
        return sp[0] in ('http+jjs:', 'https+jjs:') and not sp[1]
    @staticmethod
    def login_type(url):
        url, params = url.split('?')
        params = {k: v for k, v in (i.split('=', 1) if '=' in i else (i, None) for i in params.split('&'))}
        if 'contest' not in params:
            return ['contest_list']
        elif params.get('auth', None) == 'token':
            return ['pass']
        elif params.get('auth', None) in ('gettoken', 'guest'):
            return []
        else:
            return ['login', 'pass']
    def __init__(self, url, login, password):
        print(url)
        Backend.__init__(self)
        url, params = url.split('?')
        url = url.replace('+jjs', '', 1)
        if url.endswith('/'): url = url[:-1]
        params = {k: v for k, v in (i.split('=', 1) if '=' in i else (i, None) for i in params.split('&'))}
        contest_id = params['contest']
        if params.get('auth', None) == 'token':
            self.cookie = 'Token '+password
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
            self.cookie = 'Token '+token[3:-3]
        elif params.get('auth', None) == 'guest':
            self.cookie = 'Token Guest'
        else:
            code, headers, data = json_req(url + '/auth/simple', {'login': login, 'password': password})
            if code != 200:
                try: msg = 'Login failed: %s'%data['detail']['errorCode']
                except Exception: msg = 'Login failed.'
                raise BruteError(msg)
            self.cookie = 'Token '+data['data']
        self.url = url
        self.params = params
        self.contest = contest_id
        self.lsu_cache = {}
        self._get_cache = {}
        code, headers, data = json_req(url + '/contests/' + urlescape(self.contest), None, {'Authorization': self.cookie})
        if code != 200:
            raise BruteError('Login failed: unknown contest')
    def _cache_get(self, path):
        try: return self._get_cache[path]
        except KeyError: pass
        ans = json_req(self.url + path, None, {'Authorization': self.cookie})
        with self.cache_lock:
            if self.caching:
                self._get_cache[path] = ans
        return ans
    def stop_caching(self):
        self._get_cache.clear()
    def task_list(self):
        code, headers, data = self._cache_get('/contests/'+urlescape(self.contest)+'/problems')
        if code != 200: return []
        return [i['rel_name'] for i in data]
    def submission_list(self):
        code, headers, data = self._cache_get('/contests/'+urlescape(self.contest)+'/problems')
        if code != 200: mapping = {}
        else: mapping = {i['name']: i['rel_name'] for i in data}
        code, headers, data = self._cache_get('/runs')
        if code != 200: return [], []
        data.reverse()
        return [i['id'] for i in data if i['contest_id'] == self.contest], [mapping.get(i['problem_name'], i['problem_name']) for i in data if i['contest_id'] == self.contest]
    def submission_results(self, id):
        code, headers, data = self._cache_get('/runs/%d/protocol?compile_log=true'%int(id))
        if code != 200: return [], []
        return [self._format_status(i['status']['code']) for i in data['tests']], ['?.???' for i in data['tests']]
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
        code, headers, data = json_req(self.url+'/runs', {
            'toolchain': lang,
            'code': ''.join(base64.b64encode(text).decode('ascii').split()),
            'problem': taskid,
            'contest': self.contest
        }, {'Authorization': self.cookie})
        if code != 200:
            try: msg = 'Submit failed: '+data['detail']['errorCode']
            except: return
            else: raise BruteError(msg)
    def status(self):
        ans = {}
        with self.may_cache():
            data = list(zip(self.task_list(), self.scoreboard()[0][1]))
        for i, j in data:
            if j == None: ans[i] = None
            elif j['attempts'] < 0: ans[i] = 'Partial solution'
            else: ans[i] = 'OK'
        return ans
    def scores(self):
        with self.may_cache():
            data = list(zip(self.task_list(), self.scoreboard()[0][1]))
        return {i: (j['score'] if j != None else None) for i, j in data}
    def compiler_list(self, task):
        code, headers, data = self._cache_get('/toolchains')
        if code == 200:
            return [(i, x['id'], x['name']) for i, x in enumerate(data)]
        else:
            raise BruteError("Failed to fetch compiler list.")
    def _submission_descr(self, id):
        id = int(id)
        code, headers, data = self._cache_get('/runs')
        if code != 200: return None
        for i in data:
            if i['id'] == id:
                return i
    def _get_lsu(self, id):
        id = int(id)
        code, headers, lsu = json_req(self.url+'/runs/%d/live', None, {'Authorization': self.cookie})
        if code != 200:
            return self.lsu_cache.get(id, None)
        if lsu['finish']:
            try: del self.lsu_cache[id]
            except KeyError: pass
            return None
        with self.cache_lock:
            if id not in self.lsu_cache: self.lsu_cache[id] = {'test': None, 'score': None}
            if lsu['current_test'] != None: self.lsu_cache[id]['test'] = lsu['current_test']
            if lsu['live_score'] != None: self.lsu_cache[id]['score'] = lsu['live_score']
            return self.lsu_cache[id]
    def _format_status(self, st):
        if st == 'ACCEPTED' or st == 'TEST_PASSED' or st == 'OK': return 'OK'
        st = st.replace('_', ' ')
        return st[:1].upper()+st[1:].lower()
    def compile_error(self, id, *, binary=False, kind=None):
        if kind in (None, 1): # compiler output
            code, headers, data = self._cache_get('/runs/%d/protocol?compile_log=true')
            if code != 200: ans = None
            else: ans = base64.b64decode(data.get('compile_stdout', '').encode('ascii'))+base64.b64decode(data.get('compile_stderr', '').encode('ascii'))
        elif kind == 3: # binary
            code, headers, data = get(self.url+'/runs/%d/binary', {'Authorization': self.cookie})
            if code != 200: ans = None
            else: ans = data
        if ans != None and not binary: ans = ans.decode('utf-8', 'replace')
        return ans
    def submission_status(self, id):
        st = self._submission_descr(id)
        if st == None: return None
        lsu = self._get_lsu(id)
        if lsu != None:
            status = 'Running'
            if lsu['test'] != None: status += ', test '+str(lsu['test'])
            return status
        if st['status'] == None: return 'Running'
        return self._format_status(st['status']['code'])
    def submission_source(self, id):
        code, headers, data = self._cache_get('/runs/%d/source'%int(id))
        if code != 200: return None
        return base64.b64decode(data.encode('ascii'))
    def submission_stats(self, id):
        st = self._submission_descr(id)
        if st == None: return None
        lsu = self._get_lsu(id)
        code, headers, prot = self._cache_get('/runs/%d/protocol?compile_log=true'%int(id))
        if code != 200: prot = None
        ans = {}
        if lsu != None:
            ans['score'] = lsu['score']
            if lsu['test'] != None: ans['tests'] = {'success': lsu['test']}
        if 'subtasks' in prot and prot['subtasks']:
            prot['subtasks'].sort(key=lambda i: i['subtask_id'])
            ans['group_scores'] = [i['score'] for i in prot['subtasks']]
        return ans
    def submission_score(self, id):
        st = self._submission_descr(id)
        if st == None: return None
        lsu = self._get_lsu(id)
        if lsu != None: return lsu['score']
        else: return st['score']
    def get_samples(self, id, *, binary=False):
        def deb64(x):
            ans = base64.b64decode(x.encode('ascii'))
            if not binary: ans = ans.decode('utf-8', 'replace')
            return ans
        ans = {}
        code, headers, data = self._cache_get('/runs/%d/protocol?test_data=true&output=true&answer=true'%int(id))
        if code != 200: return ans
        for i, j in enumerate(i for i in data['tests']):
            cur = ans[i + 1] = {}
            for k1, k2 in (('test_stdin', 'Input'), ('test_stdout', 'Output'), ('test_stderr', 'Stderr'), ('test_answer', 'Correct')):
                if k1 in j and j[k1] != None: cur[k2] = deb64(j[k1])
        return ans
    def scoreboard(self):
        code, headers, data = self._cache_get('/contests/'+urlescape(self.contest)+'/standings')
        if code != 200: return []
        ans = []
        i = 1
        while str(i) in data['parties']:
            cur = data['parties'][str(i)]
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
    def contest_list(self):
        if isinstance(self, str):
            if '?' in self:
                url, params = self.split('?')
                params = {k: v for k, v in (i.split('=', 1) if '=' in i else (i, None) for i in params.split('&'))}
            else:
                url = self
                params = {}
            if url.endswith('/'): url = url[:-1]
        else:
            url = self.url
            params = dict(self.params)
        url0 = url
        url = url.replace('+jjs', '', 1)
        code, headers, data = json_req(url+'/contests', None)
        ans = []
        if code != 200: return ans
        for i in data:
            params['contest'] = i['id']
            ans.append((url0+'/?'+urllib.parse.urlencode(params), i['title'], {}))
        return ans
