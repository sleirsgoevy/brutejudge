import html, urllib.parse, brutejudge._http.types as bjtypes, brutejudge._http.html2md as html2md, collections, time, json
from brutejudge._http.base import Backend
from brutejudge._http.ejudge import get, post
from brutejudge.error import BruteError

class AtCoder(Backend):
    @staticmethod
    def detect(url):
        if url.startswith('http:'): url = 'https:' + url[5:]
        return (url+'/').startswith('https://atcoder.jp/contests/')
    def __init__(self, url, login, password):
        Backend.__init__(self)
        if url.startswith('http:'): url = 'https:' + url[5:]
        locale = 'en'
        if '#locale=' in url:
            url, locale = url.rsplit('#locale=', 1)
        if url.endswith('/'): url = url[:-1]
        code, headers, data = get('https://atcoder.jp/login')
        if code != 200:
            raise BruteError("Failed to fetch login page.")
        data = data.decode('utf-8', 'replace')
        self.cookie = next(i for i in headers['Set-Cookie'] if i.startswith('REVEL_SESSION=')).split(';', 1)[0]
        self.csrf_token = ('\0'+urllib.parse.unquote(self.cookie.split('=', 1)[1])).split('\0csrf_token:', 1)[1].split('\0', 1)[0]
        code, headers, data = post('https://atcoder.jp/login', {'username': login, 'password': password, 'csrf_token': self.csrf_token}, {'Cookie': self.cookie, 'Content-Type': 'application/x-www-form-urlencoded'})
        if code != 302 or headers['Location'] != '/home':
            raise BruteError("Login failed.")
        self.url = '/'+url.split('/', 3)[3]
        self.locale = locale
        self.cookie = next(i for i in headers['Set-Cookie'] if i.startswith('REVEL_SESSION=')).split(';', 1)[0]
        self.csrf_token = ('\0'+urllib.parse.unquote(self.cookie.split('=', 1)[1])).split('\0csrf_token:', 1)[1].split('\0', 1)[0]
        self._cache = {}
    def _cache_get(self, url):
        if url.startswith('/'):
            url = 'https://atcoder.jp'+url
        with self.cache_lock:
            if url in self._cache:
                return self._cache[url]
        ans = get(url, {'Cookie': self.cookie})
        with self.cache_lock:
            if self.caching: self._cache[url] = ans
        return ans
    def stop_caching(self):
        self._cache.clear()
    def _tasks(self):
        code, headers, data = self._cache_get(self.url+'/tasks')
        if code != 200:
            raise BruteError("Failed to fetch task list.")
        data = data.decode('utf-8', 'replace')
        task_ids = []
        task_names = []
        for i in data.split('<a href="'+self.url+'/tasks/')[1:]:
            task_id = html.unescape(i.split('"', 1)[0])
            task_name = html.unescape(i.split('>', 1)[1].split('<', 1)[0])
            task_ids.append(task_id)
            task_names.append(task_name)
        assert len(task_ids) % 2 == 0 and task_ids[::2] == task_ids[1::2]
        return list(zip(task_ids[::2], task_names[::2], task_names[1::2]))
    def tasks(self):
        return [bjtypes.task_t(i, j[1], j[2]) for i, j in enumerate(self._tasks())]
    @staticmethod
    def _decapitalize(s):
        return s[:1].upper()+s[1:].lower()
    def submissions(self):
        tasks = {i: j for i, j, k in self._tasks()}
        code, headers, data = self._cache_get(self.url+'/submissions/me')
        if code != 200:
            raise BruteError("Failed to fetch submission list.")
        data = data.decode('utf-8', 'replace')
        ans = []
        for subm in data.split('''<td class="no-break"><time class='fixtime fixtime-second'>''')[1:]:
            task_id = html.unescape(subm.split('<a href="'+self.url+'/tasks/', 1)[1].split('"', 1)[0])
            subm_id = subm.split('<td class="text-right submission-score" data-id="', 1)[1]
            subm_id, score = subm_id.split('">', 1)
            subm_id = int(subm_id)
            score = score.split('<', 1)[0].strip()
            score = int(score) if score else None
            status = self._decapitalize(html.unescape(subm.split("<span class='label", 1)[1].split(' title="', 1)[1].split('"', 1)[0]))
            ans.append(bjtypes.submission_t(subm_id, tasks[task_id], status, score, None))
        return ans
    def submission_protocol(self, subm_id):
        code, headers, data = self._cache_get(self.url+'/submissions/'+str(int(subm_id)))
        if code != 200:
            raise BruteError("Failed to fetch submission protocol.")
        data = data.decode('utf-8', 'replace')
        ans = []
        for test in data.split('<th>Case Name</th>', 1)[1].split('<tbody>', 1)[1].split('<tr>')[1:]:
            tds = test.split('<td ')[1:]
            test_name = html.unescape(tds[0].split('>', 1)[1].split('<', 1)[0])
            status = self._decapitalize(html.unescape(tds[1].split(' title="', 1)[1].split('"', 1)[0]))
            time = html.unescape(tds[2].split('>', 1)[1].split('<', 1)[0])
            memory = html.unescape(tds[3].split('>', 1)[1].split('<', 1)[0])
            assert time.endswith(' ms')
            time = int(time[:-3]) / 1000
            assert memory.endswith(' KB')
            memory = int(memory[:3]) * 1024
            ans.append(bjtypes.test_t(status, {
                'name': test_name,
                'time_usage': time,
                'memory_usage': memory,
            }))
        return ans
    def submit_solution(self, task, lang, text):
        task_id = self._tasks()[task][0]
        code, headers, data = post('https://atcoder.jp'+self.url+'/submit', {
            'data.TaskScreenName': task_id,
            'data.LanguageId': str(int(lang)),
            'sourceCode': text,
            'csrf_token': self.csrf_token,
        }, {'Cookie': self.cookie, 'Content-Type': 'application/x-www-form-urlencoded'})
        if code != 302 or headers['Location'] != self.url+'/submissions/me':
            raise BruteError("Submission failed.")
    def scores(self):
        code, headers, data = self._cache_get(self.url+'/score')
        if code != 200:
            raise BruteError("Failed to fetch score page.")
        data = data.decode('utf-8', 'replace')
        ans = collections.OrderedDict()
        for task in data.split('<tbody>', 1)[1].split('<tr class="no-break">')[1:]:
            task_name = html.unescape(task.split('<td class="text-center"><a href="', 1)[1].split('>', 1)[1].split('<', 1)[0])
            score = task.split('<td class="text-right">', 1)[1].split('<', 1)[0].strip()
            score = int(score) if score else None
            ans[task_name] = score
        return ans
    def _submission_field(self, subm_id, field_sep, sep2='<pre>'):
        code, headers, data = self._cache_get(self.url+'/submissions/'+str(int(subm_id)))
        if code != 200:
            raise BruteError("Failed to fetch the submission page.")
        data = data.decode('utf-8', 'replace')
        if field_sep not in data:
            return None
        return html.unescape((sep2+data.split(field_sep, 1)[1].split(sep2, 1)[1]).split('>', 1)[1].split('</pre>', 1)[0])
    def compile_error(self, subm_id):
        return self._submission_field(subm_id, '<h4>Compile Error</h4>')
    def submission_source(self, subm_id):
        return self._submission_field(subm_id, '<p><span class="h4">Source Code</span>', '<pre id="submission-code" data-ace-mode="').encode('utf-8')
    def do_action(self, name, *args):
        if name == 'register':
            code, headers, data = post('https://atcoder.jp'+self.url+'/register', {'csrf_token': self.csrf_token}, {'Cookie': self.cookie, 'Content-Type': 'application/x-www-form-urlencoded'})
            if code != 302 or headers['Location'] != self.url:
                raise BruteError("Registration failed.")
        elif name in ('rated_register', 'unrated_register'):
            code, headers, data = post('https://atcoder.jp'+self.url+'/register', {'csrf_token': self.csrf_token, 'rated': 'true' if name == 'rated_register' else 'false'}, {'Cookie': self.cookie, 'Content-Type': 'application/x-www-form-urlencoded'})
            if code != 302 or headers['Location'] != self.url:
                raise BruteError("Registration failed.")
    def compiler_list(self, task):
        code, headers, data = self._cache_get(self.url+'/submit')
        if code != 200:
            raise BruteError("Failed to fetch submit page.")
        data = data.decode('utf-8', 'replace')
        compilers = []
        for compiler in data.split('<div id="select-lang-', 1)[1].split('</select>', 1)[0].split('<option value="')[1:]:
            compiler_id, compiler = compiler.split('" data-ace-mode="', 1)
            short_name, compiler = compiler.split('">', 1)
            compiler_id = int(compiler_id)
            short_name = html.unescape(short_name)
            long_name = html.unescape(compiler.split('<', 1)[0])
            compilers.append(bjtypes.compiler_t(compiler_id, short_name, long_name))
        taken_ids = set()
        def get_id(s):
            if s not in taken_ids:
                return s
            sfx = 1
            while s+str(sfx) in taken_ids: sfx += 1
            return s+str(sfx)
        ans = []
        for i, j, k in sorted(compilers, key=lambda x: x[2]):
            j = get_id(j)
            taken_ids.add(j)
            ans.append(bjtypes.compiler_t(i, j, k))
        return ans
    # TODO: submission_stats
    @staticmethod
    def _parse_timestamp(s):
        dt, tm = s.split('T', 1)
        year, month, day = map(int, dt.split('-'))
        tm, tz = tm.replace('-', '+-').split('+')
        hour, minute, second = map(int, tm.split(':'))
        tzh, tzm = map(int, tz.split(':'))
        return time.mktime(time.struct_time((year, month, day, hour, minute, second, 0, 0, 0))) - 3600*tzh - 60*tzm
    @staticmethod
    def _format_duration(t):
        t, seconds = divmod(t, 60)
        t, minutes = divmod(t, 60)
        t, hours = divmod(t, 24)
        if t:
            return '%d:%02d:%02d:%02d'%(t, hours, minutes, seconds)
        else:
            return '%02d:%02d:%02d'%(hours, minutes, seconds)
    def _get_html(self, data, spc):
        return ('\n'+data.replace('\r\n', '\n').split('\n'+spc+'<span class="lang-'+self.locale+'">\n', 1)[1]).split('\n'+spc+'</span>\n', 1)[0].strip()
    def contest_info(self):
        code, headers, data = self._cache_get(self.url)
        if code != 200:
            raise BruteError("Failed to fetch the contest page.")
        data = data.decode('utf-8', 'replace')
        start_time = None
        end_time = None
        for script in (i.split('</script>', 1)[0] for i in data.split('<script>')[1:]):
            for line in map(str.strip, script.strip().split('\n')):
                if line.startswith('var startTime = moment("'):
                    start_time = line.split('"', 2)[1]
                elif line.startswith('var endTime = moment("'):
                    end_time = line.split('"', 2)[1]
        hr_data = {}
        mr_data = {}
        if start_time is not None:
            hr_data['Contest start time'] = start_time
            mr_data['contest_start'] = self._parse_timestamp(start_time)
        if end_time is not None:
            hr_data['Contest end time'] = end_time
            mr_data['contest_end'] = self._parse_timestamp(end_time)
        if start_time is not None and end_time is not None:
            mr_data['contest_duration'] = mr_data['contest_end'] - mr_data['contest_start']
            hr_data['Duration'] = self._format_duration(mr_data['contest_duration'])
        return html2md.html2md(self._get_html(data, '  ')), hr_data, mr_data
    def problem_info(self, task_id):
        code, headers, data = self._cache_get(self.url+'/tasks/'+self._tasks()[task_id][0])
        if code != 200:
            raise BruteError("Failed to fetch problem statements.")
        data = data.decode('utf-8', 'replace')
        return {}, html2md.html2md(self._get_html(data, ''))
    def _clar_list(self):
        code, headers, data = self._cache_get(self.url+'/clarifications')
        if code != 200:
            raise BruteError("Failed to fetch clarification request list.")
        data = data.decode('utf-8', 'replace')
        texts = [html.unescape(i.split('</pre>', 1)[0]) for i in data.split('<td><pre class="plain" style="word-break: break-word;">')[1:]]
        return list(zip(texts[::2], texts[1::2]))[::-1]
    def clar_list(self):
        return [bjtypes.clar_t(i, j.replace('\n', '  ').strip()) for i, (j, k) in enumerate(self._clar_list())]
    def submit_clar(self, task, subject, text):
        task = self._tasks()[task][0]
        code, headers, data = post('https://atcoder.jp'+self.url+'/clarifications/insert', {
            'taskScreenName': task,
            'question': (subject+'\n'+text).strip(),
            'csrf_token': self.csrf_token,
        }, {'Cookie': self.cookie, 'Content-Type': 'application/x-www-form-urlencoded'})
        if code != 302 or headers['Location'] != self.url + '/clarifications':
            raise BruteError("Failed to submit clarification request.")
    def read_clar(self, clar_id):
        clar = self._clar_list()[clar_id]
        return clar[0] + '\n\n' + clar[1]
    def scoreboard(self):
        code, headers, data = self._cache_get(self.url+'/standings/json')
        if code != 200:
            raise BruteError("Failed to fetch standings.")
        data = json.loads(data.decode('utf-8'))
        tasks = [i['TaskScreenName'] for i in data['TaskInfo']]
        return [({'name': i['UserName']}, [{'score': i['TaskResults'][j]['Score'] // 100, 'attempts': i['TaskResults'][j]['Elapsed'] // 10**9} if j in i['TaskResults'] else None for j in tasks]) for i in data['StandingsData']]
    def contest_list(self):
        code, headers, data = (self._cache_get if isinstance(self, AtCoder) else get)('https://atcoder.jp/contests/')
        if code != 200:
            raise BruteError("Failed to fetch contest list page.")
        data = data.decode('utf-8')
        ans = []
        for i in data.split('<a href="/contests/')[1:]:
            contest_id = html.unescape(i.split('"', 1)[0])
            contest_name = html.unescape(i.split('>', 1)[1].split('<', 1)[0])
            if contest_id and not contest_id.startswith('?'):
                ans.append((contest_name, 'https://atcoder.jp/contests/'+contest_id, {}))
        return ans
