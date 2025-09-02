import brutejudge, brutejudge._http.types as bjtypes, base64, json, urllib.parse, time, zipfile, io
from .base import Backend
from ..error import BruteError
from .ejudge import get, post

class CLICS(Backend):
    @staticmethod
    def detect(url):
        return url.startswith('clics+')
    @staticmethod
    def login_type(url):
        if '/contest/' in url:
            return ['contest_list']
        else:
            return ['login', 'password']
    def __init__(self, url, login, password):
        Backend.__init__(self)
        if url.startswith('clics+'):
            url = url[6:]
        headers = {'User-Agent': 'brutejudge/0.1'}
        if login is not None and password is not None:
            headers['Authorization'] = 'Basic '+''.join(base64.b64encode((login+':'+password).encode('utf-8')).decode('ascii').split())
        self.headers = headers
        self.url = url
        self.baseurl = self.url.rsplit('/contests/', 1)[0] + '/'
        self._cache = {}
    def contest_list(self):
        if isinstance(self, str):
            url = self
            headers = {'User-Agent': 'brutejudge/0.1'}
        else:
            url = self.url
            headers = self.headers
        if url.startswith('clics+'):
            url = url[6:]
        code, headers, data = get(url, headers)
        if code != 200:
            raise BruteError("GET %s failed: %d"%(url, code))
        data = json.loads(data.decode('utf-8'))
        return [(i['formal_name'], url + '/contests/' + i['id'], {'short_name': i['name']}) for i in data]
    def _get(self, path):
        with self.cache_lock:
            if self.caching and path in self._cache:
                return self._cache[path]
        code, headers, data = get(self.url+path, self.headers)
        if code != 200:
            raise BruteError("GET %s failed: %s"%(self.url+path, code))
        data = json.loads(data.decode('utf-8'))
        with self.cache_lock:
            if self.caching:
                if path not in self._cache:
                    self._cache[path] = data
                return self._cache[path]
            return data
    def stop_caching(self):
        self._cache.clear()
    def _tasks(self):
        data = self._get('/problems')
        if all('ordinal' in i for i in data):
            data.sort(key=lambda i: (i['ordinal'], i['id']))
        else:
            data.sort(key=lambda i: i['id'])
        return data
    def tasks(self):
        return [bjtypes.task_t(i, j['label'], j['name']) for i, j in enumerate(self._tasks())]
    @staticmethod
    def _parse_time(t):
        if t.endswith('Z'):
            timezone = 0
            t = t[:-1]
        elif '+' in t:
            t, timezone = t.rsplit('+', 1)
            timezone = int(3600 * float(timezone))
        elif '-' in t.rsplit('T', 1)[1]:
            t, timezone = t.rsplit('-', 1)
            timezone = -int(3600 * float(timezone))
        date, tm = t.split('T')
        year, month, day = map(int, date.split('-'))
        partial = 0
        if '.' in tm:
            tm, partial = tm.split('.', 1)
            partial = float('.' + partial)
        hour, minute, second = map(int, tm.split(':'))
        return time.mktime((year, month, day, hour, minute, second, -1, -1, -1)) - time.mktime(time.gmtime(0)) - timezone
    @staticmethod
    def _parse_reltime(rt):
        if '.' in rt:
            rt, partial = rt.rsplit('.', 1)
            partial = float('.'+partial)
        else:
            partial = 0
        q = rt.split(':')
        assert len(q) <= 4
        return sum(int(i)*j for i, j in zip(reversed(q), (1, 60, 3600, 86400))) + partial
    @staticmethod
    def _verdict(v):
        return {
            'AC': 'Accepted',
            'CE': 'Compilation error',
            'RTE': 'Run-time error',
            'TLE': 'Time limit exceeded',
            'WA': 'Wrong answer',
            'PE': 'Presentation error',
            'WTL': 'Wall-clock time limit exceeded',
            'ILE': 'Idleness limit exceeded',
        }.get(v, v)
    @staticmethod
    def _assign_ids(data):
        if all(i['id'].isnumeric() and (i['id'] == '0' or i['id'][:1] != '0') for i in data):
            return [int(i['id']) for i in data]
        else:
            return list(range(len(data)))
    def submissions(self):
        subms = self._get('/submissions')
        tasks = {i['id']: i['label'] for i in self._tasks()}
        subms.sort(key=lambda i: self._parse_reltime(i['contest_time']))
        subm_ids = self._assign_ids(subms)
        judgements = self._get('/judgements')
        verdicts = {i['submission_id']: i['judgement_type_id'] for i in judgements}
        scores = {i['submission_id']: i['score'] for i in judgements if 'score' in i}
        ans = [bjtypes.submission_t(i, tasks[j['problem_id']], self._verdict(verdicts.get(j['id'], 'Running...')), scores.get(j['id'], None), None) for i, j in zip(subm_ids, subms)]
        ans.reverse()
        return ans
    #TODO: submission_protocol
    def submit_solution(self, task, lang, text):
        task = self._tasks()[task]
        lang = self._compiler_list()[lang]
        if isinstance(text, str): text = text.encode('utf-8')
        headers = dict(self.headers)
        headers['Content-Type'] = 'application/json'
        code, headers, data = post(self.url+'/submissions', json.dumps({
            'problem_id': task['id'],
            'language_id': lang['id'],
            'files': [{
                'data': ''.join(base64.b64encode(text).decode('ascii').split()),
                'filename': 'solution.%s'%lang['extensions'][0] if lang.get('extensions', False) else 'solution.txt',
            }]
        }).encode('utf-8'), headers)
        if code != 200:
            raise BruteError("POST %s/submissions: %d"%(self.url, code))
    #TODO: status
    #TODO: scores
    #TODO: compile_error
    def submission_source(self, subm_id):
        subms = self._get('/submissions')
        subm_ids = self._assign_ids(subms)
        subm = subms[subm_ids.index(subm_id)]
        path = urllib.parse.urljoin(self.baseurl, subm['files'][0]['href'])
        code, headers, data = get(path, self.headers)
        if code != 200:
            raise BruteError("Get %s: %d"%(path, code))
        if subm['files'][0].get('mime', None) == 'application/zip':
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
                if len(zf.infolist()) == 1:
                    return zf.open(zf.infolist()[0]).read()
            except Exception: pass
        return data
    #TODO: action_list
    #TODO: do_action
    def _compiler_list(self):
        data = self._get('/languages')
        data.sort(key=lambda x: x['id'])
        return data
    def compiler_list(self, prob_id):
        return [bjtypes.compiler_t(i, j['id'], j['name']) for i, j in enumerate(self._compiler_list())]
    #TODO: submission_stats
    def contest_info(self):
        contest = self._get('')
        data = {}
        if 'start_time' in contest and contest['start_time'] is not None:
            data['contest_start'] = self._parse_time(contest['start_time'])
        if 'duration' in contest and contest['duration'] is not None:
            data['contest_duration'] = self._parse_reltime(contest['duration'])
        if 'contest_start' in data and 'contest_duration' in data:
            data['contest_end'] = data['contest_start'] + data['contest_duration']
        return '', {}, data
    #TODO: problem_info
    #TODO: download_file
    def _clars(self):
        clars = self._get('/clarifications')
        clars.sort(key=lambda i: self._parse_reltime(i['contest_time']))
        clar_by_id = {i['id']: idx for idx, i in enumerate(clars)}
        depth = [-1]*len(clars)
        for i in range(len(clars)):
            if depth[i] < 0:
                cur = i
                cnt = 0
                while 'reply_to_id' in clars[cur] and clars[cur]['reply_to_id'] in clar_by_id:
                    cnt += 1
                    cur = clar_by_id[clars[cur]['reply_to_id']]
                depth[cur] = 0
                cur = i
                while 'reply_to_id' in clars[cur] and clars[cur]['reply_to_id'] in clar_by_id:
                    depth[cur] = cnt
                    cnt -= 1
                    cur = clar_by_id[clars[cur]['reply_to_id']]
        indices = list(range(len(clars)))
        indices.sort(key=depth.__getitem__)
        texts = [None] * len(clars)
        titles = [None] * len(clars)
        for i in indices:
            txt = clars[i].get('text', '')
            title = txt.split('\n', 1)[0].strip()
            if 'reply_to_id' in clars[i] and clars[i]['reply_to_id'] in clar_by_id:
                txt = '> ' + texts[clar_by_id[clars[i]['reply_to_id']]].replace('\n', '\n> ') + '\n\n' + txt
                title = titles[clar_by_id[clars[i]['reply_to_id']]]
            txt = txt.rstrip()
            texts[i] = txt
            titles[i] = title
        return [(titles[i], texts[i]) for i in indices]
    def clar_list(self):
        return [bjtypes.clar_t(i, title) for i, (title, text) in enumerate(self._clars())]
    def submit_clar(self, task, subject, text):
        body = {'text': (subject + '\n\n' + text).strip()}
        if task is not None:
            body['problem_id'] = self._tasks()[task]['id']
        headers = dict(self.headers)
        headers['Content-Type'] = 'application/json'
        code, headers, data = post(self.url+'/clarifications', json.dumps(body).encode('utf-8'), headers)
        if code != 200:
            raise BruteError("POST %s/clarifications: %d"%(self.url, code))
    def read_clar(self, idx):
        return self._clars()[idx][1]
    #TODO: get_samples
    #TODO: scoreboard
