import urllib.request, urllib.parse, html, json, random, time
import brutejudge._http.types as bjtypes
from brutejudge._http.html2md import html2md
from collections import OrderedDict
from .base import Backend
from ..error import BruteError
from .openerwr import OpenerWrapper

class YaContest(Backend):
    @staticmethod
    def detect(url):
        if url.endswith('/'): url = url[:-1]
        if url.endswith('/enter'): url = url[:-6]
        return url.startswith('https://contest.yandex.ru/contest/') and url[34:].isnumeric()
    @staticmethod
    def _get_bem(data, sp):
        return json.loads(html.unescape(data.split(sp, 1)[1].split('"', 1)[0]))
    @classmethod
    def _get_sk(self, data):
        try: return data.split('<input type="hidden" name="sk" value="', 1)[1].split('"', 1)[0]
        except IndexError: return self._get_bem(data, '<div class="aside i-bem" data-bem="')['aside']['sk']
    def __init__(self, url, login, passwd):
        Backend.__init__(self)
        if url.endswith('/'): url = url[:-1]
        if url.endswith('/enter'): url = url[:-6]
        if not self.detect(url):
            raise BruteError("Not a contest.yandex.ru URL")
        self.opener = OpenerWrapper(urllib.request.build_opener(urllib.request.HTTPCookieProcessor))
        data = self.opener.open('https://passport.yandex.ru/auth?'+urllib.parse.urlencode({'origin': 'consent', 'retpath': 'https://passport.yandex.ru/profile'}), urllib.parse.urlencode({'login': login, 'passwd': passwd}).encode('ascii'))
        if data.geturl() != 'https://passport.yandex.ru/profile' and not data.geturl().startswith('https://sso.passport.yandex.ru/prepare?'):
            raise BruteError('Login failed.')
        self.url = url
        self.short_url = '/'+url.split('/', 3)[3]
    def tasks(self):
        data = self.opener.open(self.url+'/problems/').read().decode('utf-8', 'replace')
        return [bjtypes.task_t(idx, html.unescape(i), None) for idx, i in enumerate(i for i in (i.split('/', 1)[0] for i in data.split('<a class="link" href="'+self.short_url+'/problems/')[1:]) if '"' not in i)]
    @staticmethod
    def _expand_status(st):
        return {
            'WA': 'Wrong answer',
            'PE': 'Presentation error',
            'RE': 'Runtime error',
            'CE': 'Compilation error',
            'TL': 'Time limit exceeded',
            'IL': 'Idleness limit exceeded',
            # TODO: change to English
            'Тестируется': 'Testing...',
        }.get(st, st)
    def submissions(self):
        # TODO: fix this when English locale is properly supported
        data = self.opener.open(self.url+'/submits/?lang=ru').read().decode('utf-8', 'replace')
        try: submits = data.split('<table class="table table_role_submits i-bem"', 1)[1].split('</table>', 1)[0]
        except IndexError: return []
        header = []
        ans = []
        for i in submits.split('<tr class="')[1:]:
            i = i.split('>', 1)[1]
            if '<th class="' in i:
                for j in i.split('<th class="')[1:]:
                    header.append(j.split('>', 1)[1].split('</th>', 1)[0])
                header = {j: i for i, j in enumerate(header)}
                continue
            row = []
            for j in i.split('<td class="')[1:]:
                row.append(j.split('>', 1)[1].split('</td>', 1)[0])
            subm_id = int(row[header['ID']])
            task_id = html.unescape(row[header['Задача']].split('<a class="', 1)[1].split('>', 1)[1].split('</a>', 1)[0])
            status = self._expand_status(html.unescape(row[header['Вердикт']].split('<a class="', 1)[1].split('>', 1)[1].split('</a>', 1)[0]))
            test = row[header['Тест']]
            if test == '-':
                test = None
            else:
                test = int(test)
            score = row[header['Баллы']]
            if score == '-':
                score = None
            else:
                score = int(score)
            stats = {}
            if status == 'Testing...' and test is not None:
                status = 'Testing, test %d...'%test
            ans.append(bjtypes.submission_t(subm_id, task_id, status, score, test))
        return ans
    def submit_solution(self, task, lang, code):
        if isinstance(code, str): code = code.encode('utf-8')
        t = self.tasks()[task][1]
        data = self.opener.open(self.url+'/problems/'+t+'/').read().decode('utf-8', 'replace')
        prob_id = self._get_bem(data, '<div class="solution solution_type_compiler-list i-bem" data-bem="')['solution']['problemId']
        cmplrs = self._compiler_list(data)
        sk = self._get_sk(data)
        data = []
        data.append(b'')
        data.append(prob_id.encode('ascii')+b'@compilerId"\r\n\r\n'+cmplrs[lang][1].encode('ascii')+b'\r\n')
        data.append(prob_id.encode('ascii')+b'@solution"\r\n\r\ntext\r\n')
        data.append(prob_id.encode('ascii')+b'@text"\r\n\r\n'+code+b'\r\n')
        data.append(b'sk"\r\n\r\n'+sk.encode('ascii')+b'\r\n')
        data.append(b'retpath"\r\n\r\nhttps://ya.ru/\r\n')
        rand = b''
        while any(rand in i for i in data):
            rand = ('%020d'%random.randrange(10**20)).encode('ascii')
        data = (b'--'+rand+b'\r\nContent-Disposition: form-data; name="').join(data)+b'--'+rand+b'--\r\n'
        data2 = self.opener.open(urllib.request.Request(self.url+'/submit/', data, {'Content-Type': 'multipart/form-data; boundary='+rand.decode('ascii')}))
        if '?error=' in data2:
            raise BruteError('Error: '+data2.split('?error=', 1)[1])
        with self.cache_lock: self.stop_caching()
    def submission_source(self, idx):
        return self.opener.open(self.url+'/download-source/'+str(idx)).read()
    def compile_error(self, idx):
        # TODO: switch to English
        data = self.opener.open(self.url+'/run-report/'+str(idx)+'?lang=ru').read().decode('utf-8')
        try: return html.unescape(data.split('id=":hidden-info:compile-log"><div class="snippet__content"><pre class="source source_type_text">', 1)[1].split('</pre>', 1)[0])
        except IndexError: return None
    def submission_protocol(self, idx):
        data = self.opener.open(self.url+'/run-report/'+str(idx)+'?lang=ru').read().decode('utf-8').split('<table class="table table_role_tests-list">', 1)[1].split('</table>', 1)[0]
        ans = []
        for i in data.split('<tr class="')[1:]:
            rows = [j.split('>', 1)[1].split('</td>', 1)[0] for j in i.split('<td class="')[1:]]
            status = html.unescape(rows[2]).replace('-', ' ')
            status = status[:1].upper() + status[1:].lower()
            if status == 'Ok':
                status = 'OK'
            limits = html.unescape(rows[3])
            if ' / ' not in limits: limits = '- / -'
            time, memory = limits.split(' / ')
            if time.endswith('ms'):
                time = int(time[:-2]) / 1000
            else:
                time = None
            if memory.endswith('Kb'):
                memory = float(memory[:-2]) * 2**10
            elif memory.endswith('Mb'):
                memory = float(memory[:-2]) * 2**20
            elif memory.endswith('Gb'):
                memory = float(memory[:-2]) * 2**30
            else:
                memory = None
            stats = {}
            if time is not None:
                stats['time_usage'] = time
            if memory is not None:
                stats['memory_usage'] = memory
            ans.append(bjtypes.test_t(status, stats))
        return ans
    @staticmethod
    def _compiler_list(data):
        ans = []
        for i in data.split('<select class="select__control" name="')[1:]:
            if i.split('"', 1)[0].endswith('@compilerId'):
                for idx, j in enumerate(i.split('</select>', 1)[0].split('<option class="select__option" value="')[1:]):
                    short_name = html.unescape(j.split('"', 1)[0])
                    long_name = html.unescape(j.split('</option>', 1)[0].rsplit('>', 1)[1])
                    ans.append((idx, short_name, long_name))
        return ans
    def compiler_list(self, task):
        t = self.tasks()[task][1]
        data = self.opener.open(self.url+'/problems/'+t+'/').read().decode('utf-8', 'replace')
        return self._compiler_list(data)
    def do_action(self, action):
        try: url = self.url + {'stop_virtual': '/finish/?return=false', 'restart_virtual': '/finish/?return=true'}[action]
        except KeyError: pass
        else:
            try: return self.opener.open(url, urllib.parse.urlencode({'sk': self._get_sk(self.opener.open(self.url).read().decode('utf-8', 'replace'))}).encode('ascii')).read() == b'OK'
            except urllib.request.URLError: return False
        action = {'register': 'register', 'start_virtual': 'startVirtual'}[action]
        try: data = self.opener.open(self.url+'/enter/', urllib.parse.urlencode({'sk': self._get_sk(self.opener.open(self.url).read().decode('utf-8', 'replace')), 'action': action, 'retpath': self.url}).encode('ascii'))
        except urllib.request.URLError: return False
        url = data.geturl()
        return url.startswith(self.url+'/') and '?error=' not in url
    def contest_info(self):
        data = self.opener.open(self.url+'/enter?lang=en').read().decode('utf-8', 'replace')
        try: descr = data.split('<div class="post">', 1)[1].split('</div><div class="content__info">', 1)[0]
        except IndexError: descr = ''
        descr = html2md(descr)
        machine_keys = {}
        for i, j in (
            ('start', 'contest_start'),
            ('finish', 'contest_end'),
        ):
            try: value = int(data.split(i+':</div><div class="status__value inline-block"><time class="time-local i-bem" data-bem="{&quot;time-local&quot;:{&quot;timestamp&quot;:', 1)[1].split('}', 1)[0]) / 1000
            except (ValueError, IndexError): raise
            machine_keys[j] = value
        try: machine_keys['remaining_time'] = int(data.split('<div class="countdown i-bem" data-bem="{&quot;countdown&quot;:{&quot;name&quot;:&quot;refresh-timer&quot;,&quot;duration&quot;:', 1)[1].split('}', 1)[0]) / 1000
        except (ValueError, IndexError): pass
        if 'contest_start' in machine_keys and 'contest_end' in machine_keys:
            machine_keys['duration'] = machine_keys['contest_end'] - machine_keys['contest_start']
        if 'contest_end' in machine_keys and 'remaining_time' in machine_keys:
            machine_keys['server_time'] = machine_keys['contest_end'] - machine_keys['remaining_time']
        human_keys = {}
        for i, j in (
            ('Server time', 'server_time'),
            ('Start', 'contest_start'),
            ('Finish', 'contest_end'),
            ('Duration', 'duration'),
            ('Till the end', 'remaining_time')):
            if j in machine_keys:
                if j >= 'cz':
                    q = int(machine_keys[j])
                    q, seconds = divmod(q, 60)
                    q, minutes = divmod(q, 60)
                    days, hours = divmod(q, 24)
                    if days:
                        human_keys[i] = '%d:%02d:%02d:%02d'%(days, hours, minutes, seconds)
                    else:
                        human_keys[i] = '%02d:%02d:%02d'%(hours, minutes, seconds)
                else:
                    human_keys[i] = time.ctime(machine_keys[j])
        return descr, human_keys, machine_keys
    def problem_info(self, which):
        task = self.tasks()[which][1]
        data = self.opener.open(self.url+'/problems/'+urllib.parse.quote(task)+'?lang=en').read().decode('utf-8', 'replace')
        try: title = data.split('<div class="header">', 1)[1].split('<table', 1)[0]
        except IndexError: title = ''
        horz = []
        for i in data.split('<div class="header">', 1)[1].split('<div class="legend">', 1)[0].split('<th>')[1:]:
            q = html.unescape(i.split('</th>', 1)[0])
            if q:
                horz.append(q)
        params = {}
        for i in data.split('<div class="header">', 1)[1].split('<div class="legend">', 1)[0].split('<tr class="')[1:]:
            i = i.split('</tr>', 1)[0]
            values = []
            for j in i.replace('<td>', '<td class="">').replace('<td colspan="', '<td class="').split('<td class="')[1:]:
                values.append(html.unescape(j.split('>', 1)[1].split('</td>', 1)[0]))
            if len(values) == 2:
                params[values[0]] = values[1]
            elif len(values) == len(horz) + 1:
                for k, v in zip(horz, values[1:]):
                    params[values[0]+' ('+k+')'] = v
            else:
                params[values[0]] = ';; '.join(values[1:])
        try: legend = data.split('<div class="legend">', 1)[1].split('<a name="', 1)[0]
        except IndexError: legend = ''
        legend = html2md(title+legend)
        return params, legend
    def submit_clar(self, task_id, subject, text):
        form = self.opener.open(self.url+'/messages?lang=en').read().decode('utf-8', 'replace')
        sk = form.split('<input type="hidden" name="sk" value="', 1)[1].split('"', 1)[0]
        task_id = [i for i in (html.unescape(i.split('"', 1)[0]) for i in form.split('<option class="select__option" value="')[1:]) if i][task_id]
        req = self.opener.open(self.url+'/messages?lang=en', urllib.parse.urlencode({
            'sk': sk,
            'retpath': self.short_url+'/messages?lang=en',
            'problemId': task_id,
            'subject': subject,
            'message': text,
        }).encode('ascii'))
        if 'success=' not in req.geturl():
            raise BruteError("Failed to send clarification request")
    def _clar_list(self):
        data = self.opener.open(self.url+'/messages?lang=en').read().decode('utf-8', 'replace')
        ans = []
        for i in data.split('<div class="message">')[1:]:
            i = i.split('</div><div class="message">', 1)[0].split('</div><div class="page__foot">', 1)[0]
            subject = html.unescape(i.split('<h3 class="message__subject', 1)[1].split('>', 1)[1].split('<', 1)[0])
            question = html.unescape(i.split('<pre class="message__body', 1)[1].split('>', 1)[1].split('<', 1)[0])
            answer = [subject, '', question, '']
            for j in i.replace('<div class="message__answers">', '<div>').replace('<pre class="message__answer', '<div class="message__answer').split('<div class="message__answer')[1:]:
                answer.append(html.unescape(j.split('>', 1)[1].split('<', 1)[0]))
            ans.append((subject, question, '\n'.join(answer)))
        return ans[::-1]
    def clar_list(self):
        return [bjtypes.clar_t(idx, i[0]) for idx, i in enumerate(self._clar_list())]
    def read_clar(self, idx):
        q = self._clar_list()
        try: return q[idx][2]
        except IndexError: return ''
