from brutejudge._http.ejudge import get, post
from brutejudge._http.html2md import html2md
from brutejudge.http.base import Backend
from brutejudge.error import BruteError
import brutejudge._http.types as bjtypes, json, os, base64, time, collections

def handle_response(code, headers, data):
    if code in (301, 302):
        # login request is a redirect with set-cookie
        sc = headers.get('Set-Cookie', ())
        for i in ((sc,) if isinstance(sc, str) else sc):
            if i.startswith('sessionid='):
                return i.split('=', 1)[1].split(';', 1)[0]
    elif code == 200:
        return json.loads(data.decode('utf-8'))
    else:
        try: raise BruteError('%d: %s'%(code, json.loads(data.decode('utf-8'))['detail']))
        except BruteError: raise
        except Exception: raise BruteError('%d: %r'%(code, data))

def gen_csrf():
    #ans = ''.join(base64.b64encode(os.urandom(48)).decode('ascii').split())
    ans = os.urandom(32).hex()
    assert len(ans) == 64
    return ans

def get_headers(csrf, session):
    if csrf is None:
        csrf = gen_csrf()
    return {
        'Content-Type': 'application/json; charset=utf-8',
        'X-CSRFToken': csrf,
        'Cookie': 'csrftoken='+csrf+('; sessionid='+session if session is not None else ''),
        'Referer': 'https://cups.online/',
        'User-Agent': 'brutejudge'
    }

def jpost(path, data, csrf=None, session=None):
    data = json.dumps(data).encode('utf-8')
    return handle_response(*post('https://cups.online'+path, data, get_headers(csrf, session)))

def jget(path, csrf=None, session=None):
    headers = get_headers(csrf, session)
    del headers['Content-Type']
    return handle_response(*get('https://cups.online'+path, headers))

class CupsOnline(Backend):
    @staticmethod
    def detect(url):
        return url == 'https://cups.online' or url.startswith('https://cups.online/')
    def _jpost(self, path, data):
        return jpost(path, data, self.csrf, self.session)
    def _jget(self, path):
        try: return self._cache_jget[path]
        except KeyError: pass
        ans = jget(path, self.csrf, self.session)
        with self.cache_lock:
            if self.caching:
                self._cache_jget[path] = ans
        return ans
    def __init__(self, url, login, password):
        Backend.__init__(self)
        if url.startswith('https://cups.online/ru/tasks/'):
            idx = int(url.split('/', 5)[-1])
            self.round = lambda: self._jget('/api_v2/task/%d/'%idx)['round']['id']
        elif url.startswith('https://cups.online/ru/rounds/'):
            idx = int(url.split('/', 5)[-1])
            self.round = lambda: idx
        elif url.startswith('https://cups.online/ru/workareas/'):
            _, _, _, _, _, contest, rnd, task = url.split('/')
            rnd = int(rnd)
            self.round = lambda: rnd
        else:
            raise BruteError("Invalid or unsupported URL")
        self.csrf = gen_csrf()
        self.session = None
        self.session = self._jpost('/api_v2/login/', {
            'email': login,
            'password': password,
        })
        self.round = self.round()
        self._cache_jget = {}
        #self._subm2task = {}
    def stop_caching(self):
        self._cache_jget.clear()
    def tasks(self):
        return [bjtypes.task_t(i['id'], i['order_sign'], i['name']) for i in self._jget('/api_v2/round/%d/'%self.round)['tasks']]
    @staticmethod
    def _submission_verdicts(subm):
        t = subm.get('test_results', None)
        if not t: return []
        t.sort(key=lambda i: int(i['test']))
        return [i['code'] for i in t]
    @classmethod
    def _submission_status(self, subm):
        verdicts = self._submission_verdicts(subm)
        if subm['state_code'] == 2 and verdicts:
            try: status = next(i for i in verdicts if i != 'OK')
            except StopIteration: status = 'OK'
            status = self._expand_status(status)
        else:
            status = {
                0: 'Judging',
                2: 'Testing complete',
                3: 'Compiling',
                4: 'Compilation error',
            }.get(subm['state_code'], '%s (%d)'%(subm['state'], subm['state_code']))
        return status
    @staticmethod
    def _expand_status(st):
        return {
            'WA': 'Wrong answer',
            'PE': 'Presentation error',
            'RE': 'Runtime error',
            'CE': 'Compilation error',
            'TL': 'Time limit exceeded',
        }.get(st, st)
    @staticmethod
    def _to_int(q):
        if isinstance(q, float) and q == int(q):
            q = int(q)
        return q
    def submissions(self):
        tasks = self.tasks()
        ans = []
        for i in tasks:
            subms = self._jget('/api_v2/task/%d/uploaded_solutions/?page_size=1000000000'%i.id)
            for j in subms['results']:
                idx = j['id']
                status = self._submission_status(j)
                score = self._to_int(j['complete_score'])
                verdicts = self._submission_verdicts(j)
                ans.append(bjtypes.submission_t(idx, i.short_name, status, score, sum(i == 'OK' for i in verdicts)))
                #self._subm2task[idx] = i.id
        ans.sort(key=lambda i: -i.id)
        return ans
    def _get_submission(self, subm_id):
        return self._jget('/api_v2/solution/%d/'%subm_id)
        #if subm_id in self._subm2task:
        #    tasks = (self._subm2task[subm_id],)
        #else:
        #    tasks = [i.id for i in self.tasks()]
        #for i in tasks:
        #    subms = self._jget('/api_v2/task/%d/uploaded_solutions/?page_size=1000000000'%i)
        #    for j in subms['results']:
        #        if j['id'] == subm_id:
        #            return j
        #return None
    def submission_protocol(self, subm_id):
        tr = self._jget('/api_v2/solution/%d/test_results/'%subm_id)
        tr.sort(key=lambda i: int(i['test_name']))
        v = self._submission_verdicts(self._get_submission(subm_id))
        tr += [None]*(len(v)-len(tr))
        return [bjtypes.test_t(self._expand_status(i), {'time_usage': j['cpu_execution_time_s']} if j is not None else {}) for i, j in zip(v, tr)]
    def submit_solution(self, task, lang, text):
        if isinstance(text, str): text = text.encode('utf-8')
        data = []
        data.append(b'"solution"; filename="solution.txt"\r\nContent-Type: application/octet-stream\r\n\r\n'+text)
        data.append(b'"language"\r\n\r\n'+str(lang).encode('ascii'))
        data.append(b'"comment"\r\n\r\n')
        import random
        while True:
            x = b'----------'+str(random.randrange(1, 1000000000)).encode('ascii')
            for i in data:
                if x in i: break
            else: break
        data = b'\r\n'.join(b'--'+x+b'\r\nContent-Disposition: form-data; name='+i for i in data)+b'\r\n--'+x+b'--\r\n'
        headers = get_headers(self.csrf, self.session)
        headers['Content-Type'] = 'multipart/form-data; boundary='+x.decode('ascii')
        handle_response(*post('https://cups.online/api_v2/task/%d/upload_solution/'%task, data, headers))
    def _status_scores(self):
        status = {}
        scores = {}
        for i in self.tasks():
            status[i.short_name] = scores[i.short_name] = None
            subms = self._jget('/api_v2/task/%d/uploaded_solutions/?page_size=1000000000'%i.id)
            for j in subms['results']:
                if not j['is_best']: continue
                status[i.short_name] = self._submission_status(j)
                scores[i.short_name] = self._to_int(j['complete_score'])
        return status, scores
    def status(self):
        return self._status_scores()[0]
    def scores(self):
        return self._status_scores()[1]
    def compile_error(self, subm_id):
        subm = self._get_submission(subm_id)
        if subm is None:
            return None
        return subm.get('error_message', None)
    def submission_source(self, subm_id):
        headers = get_headers(self.csrf, self.session)
        del headers['Content-Type']
        code, headers, data = get('https://cups.online/api_v2/solution/%d/get_solution_file/'%subm_id, headers)
        if code != 200:
            handle_response(code, headers, data)
            raise BruteError("Failed to fetch source")
        return data
    def compiler_list(self, prob_id):
        return [bjtypes.compiler_t(i['id'], ''.join(i['extensions']).replace('.', ''), i['name']) for i in self._jget('/api_v2/task/%d/'%prob_id)['languages']]
    def submission_stats(self, subm_id):
        subm = self._get_submission(subm_id)
        v = self._submission_verdicts(subm)
        ans = {}
        total = len(v)
        ok = sum(i == 'OK' for i in v)
        fail = total - ok
        if total:
            ans['tests'] = {
                'total': total,
                'success': ok,
                'fail': fail,
            }
        score = subm.get('complete_score', None)
        if score is not None:
            ans['score'] = self._to_int(score)
        for i in ('test_score', 'try_penalty', 'time_penalty'):
            ans[i] = self._to_int(subm[i])
        return ans, ''
    @staticmethod
    def _format_duration(q):
        q, d = divmod(q, 60)
        q, c = divmod(q, 60)
        a, b = divmod(q, 24)
        if a: return '%d:%02d:%02d:%02d'%(a, b, c, d)
        else: return '%02d:%02d:%02d:%02d'%(b, c, d)
    @staticmethod
    def _parse_date(q):
        date, stime = q.split('+', 1)[0].split('T')
        year, month, day = map(int, date.split('-'))
        hour, minute, second = map(int, stime.split(':'))
        return int(time.mktime(time.struct_time((year, month, day, hour, minute, second, 0, 0, 0))) - time.mktime(time.gmtime(0)))
    def contest_info(self):
        data = self._jget('/api_v2/round/%d/'%self.round)
        ans1 = collections.OrderedDict((
            ('Contest start time', data['start_date'].replace('T', ' ')),
            ('Contest end time', data['finish_date'].replace('T', ' ')),
        ))
        ans2 = {
            'contest_start': self._parse_date(data['start_date']),
            'contest_end': self._parse_date(data['finish_date']),
        }
        ans1['Duration'] = self._format_duration(ans2['contest_end'] - ans2['contest_start'])
        return (html2md(data['description']), ans1, ans2)
    def problem_info(self, task_id):
        task = self._jget('/api_v2/task/%d/'%task_id)
        stats = collections.OrderedDict()
        stats['Time limit'] = task['cpu_limit']
        stats['Memory limit'] = task['mem_limit']
        stats['Max score'] = str(self._to_int(task['complete_score']))
        stats['Test score'] = str(self._to_int(task['test_score']))
        stats['Try penalty'] = str(self._to_int(task['try_penalty']))
        stats['Time penalty'] = str(self._to_int(task['time_penalty']))
        stats['Has sandbox'] = str(task['has_sandbox'])
        return (stats, html2md(task['description']))
    def get_samples(self, subm_id):
        tr = self._jget('/api_v2/solution/%d/test_results/'%subm_id)
        return {
            int(i['test_name']): {
                'Stderr' if i['code'] == 'RE' else 'Checker output': i['error']
            } for i in tr if 'error' in i and i['error'] is not None
        }
    def scoreboard(self):
        tasks = self.tasks()
        data = self._jget('/api_v2/round/747/fast_leaderboard/?page_size=1000000000')
        ans = []
        for i in data['results']:
            u = i['user']
            user_data = {
                'user_login': u['login'],
                'first_name': u['first_name'],
                'last_name': u['last_name'],
                'name': '%s %s (%s)'%(u['last_name'], u['first_name'], u['login'])
            }
            q = {j['task_id']: j for j in i['task_results']}
            ans.append((user_data, [{
                'score': q[i.id]['score'],
                'attempts': q[i.id]['attempts_number']
            } if i.id in q else {} for i in tasks]))
        return ans
    @staticmethod
    def login_type(url):
        if url in ('https://cups.online/', 'https://cups.online'):
            return ['contest_list']
        else:
            return ['login', 'pass']
    def contest_list(self):
        if not isinstance(self, str): return []
        data = jget('/api_v2/contests/?page_size=1000000000')
        ans = []
        for i in data['results']:
            for j in i['round_set']:
                ans.append((i['name']+' \u2014 '+j['name'], 'https://cups.online/ru/rounds/'+str(j['id']), {}))
        return ans
