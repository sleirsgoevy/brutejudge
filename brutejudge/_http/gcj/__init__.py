import base64, json, collections
from .oauth import do_oauth
from ..base import Backend
from ..ejudge import get, post
from ...error import BruteError
from ..html2md import html2md

def b64encode(s):
    return base64.b64encode(s).replace(b'=', b'').replace(b'/', b'_').replace(b'+', b'-')

def b64decode(s):
    s = s.replace(b'-', b'+').replace(b'_', b'/')
    while len(s) % 4: s += b'='
    return base64.b64decode(s)

class GCJ(Backend):
    @staticmethod
    def detect(url):
        url = url.split('/')
        return url[:3] == ['https:', '', 'codingcompetitions.withgoogle.com'] and url[4] == 'round'
    @staticmethod
    def login_type(url):
        return ['goauth:email profile openid https://www.googleapis.com/auth/codejam']
    def __init__(self, url, login, password, token=None):
        Backend.__init__(self)
        self.round = url.split('#', 1)[0].split('/')[5]
        if not set(self.round).issubset('0123456789abcdef'):
            raise BruteError("Invalid GCJ URL supplied")
        self.token = token if token != None else do_oauth(url, login, password)
#       self.email = login #not used
        self._get_cache = {}
        code, headers, data = self._json_req('https://codejam.googleapis.com/dashboard/%s/poll'%self.round, {})
        if code != 200:
            raise BruteError("Invalid contest ID")
    def _cache_get(self, url):
        with self.cache_lock:
            if url in self._get_cache:
                return self._get_cache[url]
        ans = get(url, {'Authorization': 'Bearer '+self.token})
        with self.cache_lock:
            if self.caching: self._get_cache[url] = ans
        return ans
    def _json_req(self, url, data, *, eout=True, ein=True, do_post=False):
        if eout: data = b64encode(json.dumps(data).encode('utf-8')).decode('ascii')
        if do_post: code, headers, data = post(url, {'p': data}, {'Authorization': 'Bearer '+self.token})
        else: code, headers, data = self._cache_get(url+'?p='+data)
        if ein: data = json.loads(b64decode(data).decode('utf-8', 'replace'))
        return code, headers, data
    def _get_which(self, which, error=None, data={}):
        code, headers, data = self._json_req('https://codejam.googleapis.com/%s/%s/poll'%(which, self.round), data)
        if code != 200 and error:
            raise BruteError(error)
        return data
    def _debug_req(self, which, data={}):
        import pprint, pydoc
        pydoc.pager(pprint.pformat(self._json_req('https://codejam.googleapis.com/%s/%s/poll'%(which, self.round), data)))
    def task_ids(self):
        data = self._get_which('dashboard', "Failed to fetch task list.")
        return [int(i['id'], 16) for i in data['challenge']['tasks']]
    def task_list(self):
        return [hex(i)[2:] for i in self.task_ids()]
    def submission_list(self):
        data = self._get_which('attempts', "Failed to fetch submission list.")
        return [int(i['id'], 16) for i in data['attempts']], [hex(int(i['task_id'], 16))[2:] for i in data['attempts']]
    @staticmethod
    def _convert_verdict(s):
        s = s.replace('_', ' ')
        s = s[:1].upper()+s[1:].lower()
        if s == 'Correct':
            return 'OK'
        return s
    def _submission_descr(self, subm_id):
        subm_id = int(subm_id)
        data = self._get_which('attempts', "Failed to fetch submission list.")
        for i in data['attempts']:
            if int(i['id'], 16) == subm_id:
                return i
        return None
    def _submission_results(self, subm_id):
        subm = self._submission_descr(subm_id)
        if subm == None: return None
        try: subm = subm['judgement']['results']
        except KeyError: return 'Pending judgement'
        return [self._convert_verdict(i['verdict__str']) for i in subm], ['%0.3f'%(i['running_time_nanos']/1000000000) for i in subm]
    def submission_results(self, subm_id):
        ans = self._submission_results(subm_id)
        if not isinstance(ans, tuple): ans = ([], [])
        return ans
    def submit(self, task, lang, code):
        if isinstance(code, bytes): code = code.decode('utf-8', 'replace')
        try: tasks = self._get_which('dashboard', '')
        except BruteError: return
        else:
            try: task = tasks['challenge']['tasks'][task]['id']
            except IndexError: return
        self._json_req('https://codejam.googleapis.com/dashboard/%s/submit'%self.round, {'code': code, 'language_id': lang, 'task_id': task}, do_post=True)
        with self.cache_lock: self.stop_caching()
    def status(self):
        user_data = {}
        data = self._get_which('scoreboard', "Failed to fetch scoreboard.", {'num_consecutive_users': 0})
        for i in data['user_scores'][0]['task_info']:
            user_data[i['task_id']] = i['tests_definitely_solved'] + i['tests_possibly_solved']
        ans = collections.OrderedDict()
        for i in data['challenge']['tasks']:
            i_ = hex(int(i['id'], 16))[2:]
            st = None
            if i['id'] in user_data:
                st = 'OK' if user_data[i['id']] == sum(1 if j['value'] else 0 for j in i['tests']) else 'Partial solution'
            ans[i_] = st
        return ans
    def scores(self):
        user_data = {}
        data = self._get_which('scoreboard', "Failed to fetch scoreboard.", {'num_consecutive_users': 0})
        for i in data['user_scores'][0]['task_info']:
            user_data[i['task_id']] = i['score']
        ans = collections.OrderedDict()
        for i in data['challenge']['tasks']:
            i_ = hex(int(i['id'], 16))[2:]
            sc = None
            if i['id'] in user_data:
                sc = user_data[i['id']]
            ans[i_] = sc
        return ans
    def compile_error(self, subm_id):
        data = self._submission_descr(subm_id)
        if data == None: return None
        try: return data['judgement']['compilation_output']
        except KeyError: return None
    def submission_status(self, subm_id):
        a = self._submission_results(subm_id)
        if not isinstance(a, tuple): return a
        return a[0][-1]
    def submission_source(self, subm_id):
        data = self._submission_descr(subm_id)
        if data == None: return None
        return data['src_content'].encode('utf-8')
    def do_action(self, *args):
        raise BruteError("Actions are not supported on GCJ.")
    def compiler_list(self, task):
        return [(i['id'], i['id__str'].lower(), i['name']) for i in self._get_which('dashboard', "Failed to fetch compiler list.")['languages']]
    def submission_stats(self, subm_id):
        data = self._get_which('attempts')
        for subm in data['attempts']:
            if int(subm['id'], 16) == subm_id: break
        else: return ({}, None)
        for task in data['challenge']['tasks']:
            if int(task['id'], 16) == int(subm['task_id'], 16):
                break
        else: task = {}
        ans = {'score': 0}
        ans['tests'] = {'total': 0, 'success': 0, 'fail': 0}
        for i, j in zip(subm.get('judgement', {}).get('results', ()), task.get('tests', 0)):
            if i['verdict__str'] == 'CORRECT': ans['score'] += j['value']
#       for i in subm.get('judgement', {}).get('results', ()):
            if j['value'] != 0:
                ans['tests']['success' if i['verdict__str'] == 'CORRECT' else 'fail'] += 1
                ans['tests']['total'] += 1
        return (ans, None)
    def problem_info(self, task):
        for i in self._get_which('dashboard')['challenge']['tasks']:
            if int(i['id'], 16) == task:
                return ({}, html2md(i['statement']))
    def submission_score(self, subm_id):
        return self.submission_stats(subm_id)[0].get('score', None)
    def stop_caching(self):
        self._get_cache.clear()
    def clars(self): return [] #STUB
