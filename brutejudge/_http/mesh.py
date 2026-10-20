import json, collections, time
import brutejudge._http.types as bjtypes
from brutejudge._http.ejudge import get, post
from brutejudge._http.base import Backend
from brutejudge._http.html2md import html2md
from brutejudge.error import BruteError

TASK_STATUSES = {
    'PART_CORRECT': 'Partial solution',
    'CORRECT': 'OK',
    'UNCOMPLETED': None,
}

SUBMISSION_STATUSES = {
    'PART_CORRECT': 'Partial solution',
    'CORRECT': 'OK',
}

TEST_STATUSES = {
    'SUCCESS': 'OK',
    'WRONG': 'Wrong answer',
}

class MESh(Backend):
    @staticmethod
    def detect(url):
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        return url.startswith('https://school.mos.ru/vrlabs/informatics/headless/olympiad/')
    @staticmethod
    def login_type(url):
        return ['cookie']
    def __init__(self, url, login, password, *, cookie=None):
        Backend.__init__(self)
        if login is not None or password is not None or cookie is None:
            raise BruteError("Only cookie login is supported for MESh (yet).")
        self.headers = {'Authorization': 'Bearer '+cookie}
        sp = url.split('?', 1)[0].split('/')
        self.api_base = '/'.join(sp[:5]) + '/api'
        self._olympiad = int(sp[7])
        if sp[8:10] == ['participation', 'results']:
            self._inner_id = int(sp[10])
        else:
            self._inner_id = None
        self._api_cache = {}
        self._meta_cache = None
        self._name_cache = {}
        self._names = []
    def _name_to_id(self, name):
        with self.cache_lock:
            if name not in self._name_cache:
                self._name_cache[name] = len(self._name_cache)
                self._names.append(name)
            return self._name_cache[name]
    def _get(self, url):
        with self.cache_lock:
            if url in self._api_cache: return self._api_cache[url]
        code, headers, data = get(self.api_base + url, self.headers)
        if code != 200:
            raise BruteError("API request failed: "+url)
        ans = json.loads(data.decode('utf-8', 'replace'))
        with self.cache_lock:
            if self.caching:
                self._api_cache[url] = ans
        return ans
    def _post(self, url, data):
        code, headers, data = post(self.api_base + url, json.dumps(data).encode('utf-8'), self.headers)
        with self.cache_lock:
            self.stop_caching()
        if code != 200:
            raise BruteError("API request failed: "+url)
        return json.loads(data.decode('utf-8', 'replace'))
    def _fetch_meta(self):
        with self.cache_lock:
            if self._meta_cache is not None:
                return self._meta_cache
        if self._inner_id is None:
            raise BruteError("Virtual contest not started.")
        ans = self._get('/pass-test/%d/state'%self._inner_id)
        with self.cache_lock:
            if self.caching:
                self._meta_cache = ans
        return ans
    def _start_virtual(self):
        data = self._post('/pass-test/%d/start?trialPass=false'%self._olympiad, {'schoolBookOnly': False})
        data['timeLimit'] *= 60
        with self.cache_lock:
            if self.caching:
                self._meta_cache = json.loads(data.decode('utf-8'))
        return data
    def stop_caching(self):
        self._api_cache.clear()
        self._meta_cache = None
    def tasks(self):
        ans = [bjtypes.task_t(i['task']['id'], str(i['task']['order']), i['task']['name']) for i in self._fetch_meta()['tasks']]
        ans.sort(key=lambda i: int(i[1]))
        return ans
    def _fetch_task(self, task_id):
        return self._get('/pass-test/%d/task/%d'%(self._inner_id, task_id))
    def submissions(self):
        submissions = []
        for i, short_name, name in self.tasks():
            for j in self._get('/task-attempt/%d/history-lite' % self._fetch_task(i)['taskAssignment']['id']):
                submissions.append(bjtypes.submission_t(j['id'], short_name, SUBMISSION_STATUSES.get(j['attemptResult'], j['attemptResult']), j.get('pointCount', None), None))
        submissions.sort(key=lambda i: -i[0])
        return submissions
    def _submission_protocol(self, subm_id):
        return self._get('/task-attempt/%d/check-result'%subm_id)
    def submission_protocol(self, subm_id):
        return [bjtypes.test_t(TEST_STATUSES.get(i['unitTestResult'], i['unitTestResult']), {
            'time_usage': i['timeSpent'],
            'memory_usage': i['memoryUsed'],
            'score': i.get('value', None)
        }) for i in self._submission_protocol(subm_id).get('unitTests', [])]
    def submit_solution(self, task, lang, text):
        if isinstance(text, bytes): text = text.decode('utf-8', 'replace')
        self._post('/task-attempt/send-answer', {
            'content': text,
            'translatorCode': self._names[lang],
            'assignmentTaskId': self._fetch_task(task)['taskAssignment']['id'],
        })
    def status(self):
        ans = collections.OrderedDict()
        for i in sorted(self._fetch_meta()['tasks'], key=lambda i: i['task']['order']):
            ans[str(i['task']['order'])] = TASK_STATUSES.get(i['checkResult'], i['checkResult'])
        return ans
    def scores(self):
        ans = collections.OrderedDict()
        for i in sorted(self._fetch_meta()['tasks'], key=lambda i: i['task']['order']):
            ans[str(i['task']['order'])] = i.get('collectedPoint', None) if i['checkResult'] != 'UNCOMPLETED' else None
        return ans
    #XXX: missing compile_error
    def submission_source(self, subm_id):
        try: subm = next(i for i in self._get('/task-attempt/%d/history-lite' % self._submission_protocol(subm_id)['assignmentTaskId']) if i['id'] == subm_id)
        except StopIteration: return None
        source = subm.get('sourceCode', None)
        if source is not None: source = source.encode('utf-8')
        return source
    def action_list(self):
        return ['start_virtual']
    def do_action(self, name, *args):
        if name != 'start_virtual':
            raise BruteError('Invalid action '+name)
        self._start_virtual()
    def compiler_list(self, prob_id):
        return [bjtypes.compiler_t(self._name_to_id(i['translatorCode']), i['translatorCode'], i['name']) for i in self._get('/supported-languages/')]
    def submission_stats(self, subm_id):
        protocol = self._submission_protocol(subm_id)
        total = len(protocol['unitTests'])
        success = sum(1 for i in protocol['unitTests'] if i.get('unitTestResult') == 'SUCCESS')
        fail = total - success
        ans = {'tests': {'total': total, 'success': success, 'fail': fail}}
        try: ans['score'] = next(i for i in self._get('/task-attempt/%d/history-lite' % protocol['assignmentTaskId']) if i['id'] == subm_id).get('pointCount', None)
        except StopIteration: ans['score'] = None
        return ans, None
    @staticmethod
    def _parse_date(date):
        assert date.endswith('Z')
        date, tm = date.split('T', 1)
        year, month, day = map(int, date.split('-'))
        hour, minute, second = tm[:-1].split(':')
        hour = int(hour)
        minute = int(minute)
        second = float(second)
        return time.mktime((year, month, day, hour, minute, int(second), 0, 0, 0)) - time.mktime((1970, 1, 1, 0, 0, 0, 0, 0, 0)) + second % 1
    @staticmethod
    def _format_duration(q):
        q, d = divmod(q, 60)
        q, c = divmod(q, 60)
        a, b = divmod(q, 24)
        if a: return '%d:%02d:%02d:%02d'%(a, b, c, d)
        else: return '%02d:%02d:%02d'%(b, c, d)
    def contest_info(self):
        meta = self._fetch_meta()
        data = {}
        data['contest_start'] = self._parse_date(meta['startDate'])
        if 'completeDate' in meta:
            data['contest_end'] = self._parse_date(meta['completeDate'])
        elif 'timeLimit' in meta:
            data['contest_end'] = data['contest_start'] + meta['timeLimit']
        if 'contest_end' in data:
            data['duration'] = data['contest_end'] - data['contest_start']
        if 'timeLimit' in meta and 'timeLeft' in meta:
            data['contest_time'] = meta['timeLimit'] - meta['timeLeft']
            data['server_time'] = data['contest_start'] + data['contest_time']
        hr_data = {}
        for i, j in (
            ('contest_start', 'Contest start time'),
            ('contest_end', 'Contest end time'),
            ('server_time', 'Server time')
        ):
            if i in data:
                hr_data[j] = time.ctime(data[i])
        for i, j in (
            ('duration', 'Duration'),
            ('contest_time', 'Contest time')
        ):
            if i in data:
                hr_data[j] = self._format_duration(data[i])
        return meta['name'], hr_data, data
    def problem_info(self, prob_id):
        task = self._fetch_task(prob_id)
        meta = {
            'Time limit': '%d s'%task['executionTimeout'],
            'Memory limit': '%d MB'%task['memoryLimit'],
        }
        statements = []
        statements.append('# ' + task['name'])
        if task.get('description', None) is not None:
            statements.append('# Description')
            statements.append(html2md(task['description']).strip())
        if task.get('inputFormat', None) is not None:
            statements.append('# Input format')
            statements.append(html2md(task['inputFormat']).strip())
        if task.get('outputFormat', None) is not None:
            statements.append('# Output format')
            statements.append(html2md(task['outputFormat']).strip())
        if task.get('examples', None) is not None:
            statements.append('# Sample tests')
            for i in task['examples']:
                statements.append('## Input')
                statements.append('```\n%s\n```'%i['exampleInput'].rstrip())
                statements.append('## Output')
                statements.append('```\n%s\n```'%i['exampleOutput'].rstrip())
                if i.get('comment', None) is not None:
                    statements.append('# Comment')
                    statements.append(html2md(i['comment']).strip())
        return meta, '\n\n'.join(statements) + '\n'
    def get_samples(self, prob_id):
        data = {}
        for idx, i in enumerate(self._submission_protocol(prob_id)['unitTests']):
            q = {}
            for k, kk in (
                ('inputData', 'Input'),
                ('outputData', 'Output'),
                ('targetData', 'Correct'),
                ('outputError', 'Checker output' if i['unitTestResult'] in ('SUCCESS', 'WRONG') else 'Stderr'),
            ):
                if k in i and i[k] is not None:
                    q[kk] = i[k]
            if q:
                data[idx+1] = q
        return data
