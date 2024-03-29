from brutejudge._http.ejudge import Ejudge, do_http, get, post
from brutejudge._http.ejudge.ej371 import get_urls
from brutejudge.error import BruteError
from brutejudge._http.base import Backend
import json, base64, collections, math
import brutejudge._http.types as bjtypes

def mbjson(x):
    try: return json.loads(x)
    except json.JSONDecodeError: return None

def mb_problem_status(x):
    try: x = x.decode('utf-8')
    except UnicodeDecodeError: return None
    x = x.split('\n')
    add_later = {}
    y = []
    for i in x:
        #if i.startswith('      "input_file": '):
        #    add_later['input_file'] = i[20:-1]
        #elif i.startswith('      "output_file": '):
        #    add_later['output_file'] = i[21:-1]
        #else:
        y.append(i)
    y = '\n'.join(y)
    try: y = json.loads(y)
    except json.JSONDecodeError: return None
    y.update(add_later)
    return y

STATUS_NAMES = {i: j for i, j in enumerate(('OK', 'Compilation error', 'Run-time error', 'Time-limit exceeded', 'Presentation error', 'Wrong answer', 'Check failed', 'Partial solution', 'Accepted for testing', 'Ignored', 'Disqualified', 'Pending check', 'Memory limit exceeded', 'Security violation', 'Style violation', 'Wall time-limit exceeded', 'Pending review', 'Rejected', 'Skipped', 'Synchronization error'))}
STATUS_NAMES[23] = 'Summoned for defense'
STATUS_NAMES[95] = 'Full rejudge'
STATUS_NAMES[96] = 'Running...'
STATUS_NAMES[97] = 'Compiled...'
STATUS_NAMES[98] = 'Compiling...'
STATUS_NAMES[99] = 'Available for testing'

class EJFuse(Ejudge):
    @staticmethod
    def detect(url):
        return url.startswith('ejfuse:')
    def __init__(self, url, login, password):
        Backend.__init__(self)
        assert url.startswith('ejfuse:http://') or url.startswith('ejfuse:https://')
        url = url[7:].replace('/new-register?', '/new-client?').replace('/new-client?', '/client?')
        contest_id = url.split("contest_id=")[1].split("&")[0]
        self.contest_id = int(contest_id)
        base_url = url.split("/client?")[0]
        code, headers, data = post(base_url+'/register', {'action': 'login-json', 'login': login, 'password': password, 'json': 1})
        data = mbjson(data)
        if code != 200 or not data or not data['ok']:
            raise BruteError("Login failed.")
        self.url = base_url+'/register'
        self.cookies = (data['result']['SID'], data['result']['EJSID'])
        code, headers, data = post(self.url, {'SID': self.cookies[0], 'EJSID': self.cookies[1], 'action': 'enter-contest-json', 'contest_id': self.contest_id, 'json': 1})
        data = mbjson(data)
        if code != 200 or not data or not data['ok']:
            raise BruteError("Login failed.")
        self.url = base_url+'/client'
        self.cookies = (data['result']['SID'], data['result']['EJSID'])
        # will fall back to normal ejudge if an unimplemented feature is encountered
        self.urls = get_urls(base_url+'/new-client?SID='+self.cookies[0])
        self.cookie = 'EJSID='+self.cookies[1]
        self._get_cache = {}
    def tasks(self):
        code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=contest-status-json&json=1'%self.cookies, False)
        data = mbjson(data)
        if code != 200 or not data or not data['ok']:
            raise BruteError("Failed to fetch task list.")
        return [bjtypes.task_t(i['id'], i['short_name'], i['long_name']) for i in data['result']['problems']]
    def _submission_list(self):
        code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=list-runs-json&prob_id=0&json=1'%self.cookies, False)
        data = mbjson(data)
        if code != 200 or not data or not data['ok']:
            raise BruteError("Failed to fetch submission list.")
        return data['result']['runs']
    def submissions(self):
        data = self._submission_list()
        ti, tl, tll = list(zip(*self.tasks()))
        ti = {j:i for i, j in enumerate(ti)}
        return [bjtypes.submission_t(i['run_id'], tl[ti[i['prob_id']]], STATUS_NAMES[i['status']], i.get('score', None), None) for i in data]
    def _submission_descr(self, run_id):
        code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=run-status-json&run_id=%%d&json=1'%self.cookies%int(run_id), False)
        data = mbjson(data)
        if code != 200 or not data or not data['ok']:
            raise BruteError("Failed to fetch testing protocol.")
        return data['result']
    def submission_protocol(self, run_id):
        data = self._submission_descr(run_id)
        try: data = data['testing_report']['tests']
        except KeyError: return [], []
        return [bjtypes.test_t(STATUS_NAMES[i['status']], {'time_usage': i['time_ms'] / 1000}) for i in data]
#   def submit(self, task, lang, text):
#       if isinstance(text, str): text = text.encode('utf-8')
#       try: task = self.task_ids()[task]#task += 1
#       except IndexError: return
#       data = []
#       data.append(b'"SID"\r\n\r\n'+self.cookies[0].encode('ascii'))
#       data.append(b'"EJSID"\r\n\r\n'+self.cookies[1].encode('ascii'))
#       data.append(b'"prob_id"\r\n\r\n'+str(task).encode('ascii'))
#       data.append(b'"lang_id"\r\n\r\n'+str(lang).encode('ascii'))
#       data.append(b'"file"; filename="brute.txt"\r\nContent-Type'
#                   b': text/plain\r\n\r\n'+text)
#       data.append(b'"JSON"\r\n\r\n1')
#       import random
#       while True:
#           x = b'----------'+str(random.randrange(1, 1000000000)).encode('ascii')
#           for i in data:
#               if x in i: break
#           else: break
#       x = '-----------------------------850577185583170701784494929'
#       data = b'\r\n'.join(b'--'+x+b'\r\nContent-Disposition: form-data; name='+i for i in data)+b'\r\n--'+x+b'--\r\n'
#       return post(self.url, data, {'Content-Type': 'multipart/form-data; boundary='+x.decode('ascii')})
    def status(self):
        tli = self.tasks()
        sl = self._submission_list()
        ans = collections.OrderedDict()
        for task in tli:
            code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=problem-status-json&problem=%%d&json=1'%self.cookies%task.id, False)
            data = mb_problem_status(data)
            if code != 200 or not data or not data['ok']:
                raise BruteError("Failed to fetch task list.")
            try: best_run = data['result']['problem_status']['best_run']
            except KeyError: ans[task.short_name] = None
            else:
                for j in sl:
                    if j['run_id'] == best_run:
                        st = STATUS_NAMES[j['status']]
                        if st not in ('OK', 'Compiling...', 'Running...', 'Compilation error', 'Pending review', 'Pending check', 'Rejected', 'Style violation'):
                            st = 'Partial solution'
                        ans[task.short_name] = st
                        break
                else: ans[task.short_name] = None
        return ans
    def scores(self):
        tli = self.tasks()
        ans = collections.OrderedDict()
        for task in tli:
            code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=problem-status-json&problem=%%d&json=1'%self.cookies%task.id, False)
            data = mb_problem_status(data)
            if code != 200 or not data or not data['ok']:
                raise BruteError("Failed to fetch task list.")
            try: ans[task.short_name] = data['result']['problem_status']['best_score']
            except KeyError: ans[task.short_name] = None
        return ans
    def compile_error(self, subm_id, *, binary=False, kind=None):
        def _decode_bytes(x):
            x = base64.b64decode(x['content']['data'])
            if binary: return x
            return x.decode('utf-8', 'replace')
        subm = self._submission_descr(subm_id)
        if 'testing_report' in subm and 'valuer_comment' in subm['testing_report'] and kind in (None, 2):
            return _decode_bytes(subm['testing_report']['valuer_comment'])
        elif 'compiler_output' in subm and kind in (None, 1):
            return _decode_bytes(subm['compiler_output'])
        else:
            return None
    def submission_status(self, subm_id):
        sl = self._submission_list()
        for i in sl:
            if i['run_id'] == subm_id:
                return STATUS_NAMES[i['status']]
        return None
    def submission_source(self, subm_id):
        code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=download-run&run_id=%%d&json=1'%self.cookies%subm_id, False)
        if code != 200 or headers.get('Content-Type', None) == 'text/json': return None
        return data
#   def do_action(self, subm_id):
#       raise BruteError("Not supported on ejudge-fuse")
    def compiler_list(self, prob_id):
        code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=contest-status-json&json=1'%self.cookies, False)
        data = mbjson(data)
        if code != 200 or not data or not data['ok']:
            raise BruteError("Failed to fetch compiler list.")
        return [bjtypes.compiler_t(i['id'], i['short_name'], i['long_name']) for i in data['result']['compilers']]
    def contest_info(self):
        code, headers, data = self._cache_get(self.url+'?SID=%s&EJSID=%s&action=contest-status-json&json=1'%self.cookies, False)
        data = mbjson(data)
        if code != 200 or not data or not data['ok']:
            raise BruteError("Failed to fetch contest info.")
        datas = {}
        data1 = {}
        ctst = data['result']['contest']
        ctst.update(data)
        #datas['Server time:'] = data1['server_time'] = data['server_time']
        data1['server_time'] = data['server_time']
        #datas['Contest start time'] = data1['contest_start'] = ctst['start_time']
        data1['contest_start'] = ctst['start_time']
        #datas['Duration:'] = data1['contest_duration'] = math.inf if ctst['is_unlimited'] else ctst['duration']
        data1['contest_duration'] = math.inf if ctst['is_unlimited'] else ctst['duration']
        if 'end_time' in data:
            data1['contest_end'] = data['end_time']
        elif 'contest_start' in data1 and 'contest_duration' in data1:
            data1['contest_end'] = data1['contest_start'] + data1['contest_duration']
        if 'server_time' in data1 and 'contest_start' in data1:
            data1['contest_time'] = data1['server_time'] - data1['contest_start']
        return ('', datas, data1)
    def submission_stats(self, subm_id):
        subm = self._submission_descr(subm_id)
        ans = {}
        if 'score' in subm['run']: ans['score'] = subm['run']['score']
        tests = {}
        if 'passed_tests' in subm['run']: tests['success'] = subm['run']['passed_tests']
        if 'tests' in subm: tests['total'] = len(subm['tests'])
        if 'total' in tests and 'success' in tests:
            tests['fail'] = tests['total'] - tests['success']
        if tests: ans['tests'] = tests
        return (ans, None)
    #TODO
    def submission_score(self, subm_id):
        for i in self._submission_list():
            if i['run_id'] == subm_id:
                return i.get('score', None)
        return None
    def get_samples(self, subm_id):
        return self._get_samples(Ejudge.compile_error(self, subm_id))
