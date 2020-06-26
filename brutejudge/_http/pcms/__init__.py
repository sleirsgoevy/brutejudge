import collections, ast, html
from .libpcms import PCMS as LPCMS
from brutejudge._http.base import Backend
from brutejudge.error import BruteError
import brutejudge._http.html2md as html2md
import brutejudge._http.types as bjtypes

class PCMS(Backend):
    @staticmethod
    def detect(url):
        return LPCMS.detect(url)
    def __init__(self, url, login, password):
        Backend.__init__(self)
        try: self.pcms = LPCMS(url, (login, password))
        except AssertionError as e: raise BruteError(str(e))
        self._subms = []
        self._subms_set = set()
        self._clars = []
        self._messages = []
        self._user_clars = []
        self._user_clars_set = set()
        self.pcms.set_locale('English')
        self._call_cache = {}
        self.submission_list()
    @staticmethod
    def _remove_tags(t):
        t = t.split('<')
        return t[0] + ''.join(i.split('>', 1)[-1] for i in t[1:])
    def _cache_call(self, func, *args):
        with self.cache_lock:
            if (func, args) in self._call_cache: return self._call_cache[func, args]
        ans = func(*args)
        with self.cache_lock:
            if self.caching: self._call_cache[func, args] = ans
        return ans
    def tasks(self):
        try: return [bjtypes.task_t(i, j, None) for i, j in enumerate(self.pcms.get_submit()[0])]
        except: raise BruteError("Failed to fetch task list.")
    def submissions(self):
        x = self._cache_call(self.pcms.get_submissions)
        x = list(sorted(x.items(), key=lambda x:x[0]))
        data = []
        sid_to_subm = {}
        for t, (k, v) in enumerate(x):
            for i in v:
                sid = int(i[1]['attempt']) * len(x) + t
                sid_to_subm[sid] = i
                data.append((int(i[1]['time'].replace(':', '')), int(i[1]['attempt']), sid, k))
        data.sort()
        for _, _, i, j in data:
            if i not in self._subms_set:
                self._subms_set.add(i)
                self._subms.append((i, j))
        ans = []
        for sid, task_id in reversed(self._subms):
            try: subm = sid_to_subm[sid]
            except KeyError: status = score = oktests = None
            else:
                status = self._remove_tags(subm['outcome']) if 'outcome' in subm else None
                if status == 'Accepted': status = 'OK'
                score = int(subm['score'].split(' = ', 1)[1]) if 'score' in subm else None
                ans.append(bjtypes.submission_t(sid, task_id, status, score, None))
        return ans
    def _decode_subm_id(self, subm_id):
        subm_id = int(subm_id)
        tasks = self.task_list()
        attempt, taskid = divmod(subm_id, len(tasks))
        task = tasks[taskid]
        return (task, attempt)
    def submission_protocol(self, subm_id):
        task, attempt = self._decode_subm_id(subm_id)
        proto = self._cache_call(self.pcms.get_protocol, task, attempt)
        if proto == None:
            raise BruteError("Failed to fetch testing protocol.")
        ans = []
        for i in proto:
            if 'outcome' not in i[1]: continue
            outcome = self._remove_tags(i[1]['outcome'])
            if outcome == 'Accepted': outcome = 'OK'
            stats = {}
            try:
                stats['time_usage'] = int(i[1]['time'].split()[0]) / 1000
            except KeyError: pass
            if 'memory' in i[1]:
                m = i[1]['memory']
                if m.endswith('KB'): m = int(m[:2])*1024
                elif m.endswith('MB'): m = int(m[:2])*1048576
                else: assert False
                stats['memory_usage'] = m
            ans.append(bjtypes.test_t(outcome, stats))
        return ans
    def submit_solution(self, taskid, lang, text):
        tasks, langs, exts, vs = self._cache_call(self.pcms.get_submit)
        task = tasks[taskid]
        lang = [j for i, j, k in self.compiler_list(taskid) if i == lang][0]
        if isinstance(text, str):
            text = text.encode('utf-8')
        try: self.pcms.submit(task, lang, text, vs, {i[lang] for i in exts.values() if lang in i}.pop())
        except AssertionError: pass
        with self.cache_lock: self.stop_caching()
    def status(self):
        x = self._cache_call(self.pcms.get_submissions)
        ans = collections.OrderedDict()
        for k, v in x.items():
            if v:
                ans[k] = self._remove_tags(v[-1][1]['outcome']) if 'outcome' in v[-1][1] else None
            else:
                ans[k] = None
        return ans
    def scores(self):
        x = self._cache_call(self.pcms.get_submissions, False)
        ans = {}
        for k, v in x.items():
            notnone = False
            for i in v:
                if i[0].startswith('run '):
                    notnone = True
                    ans[k] = ans.get(k, 0)
                if i[0] == 'always' and 'head total-score' in i[1]:
                    ans[k] = int(i[1]['head total-score'].split('<span>Score =', 1)[1].split('</span>', 1)[0])
            if not notnone: ans[k] = None
        return ans
    def compile_error(self, subm_id):
        task, attempt = self._decode_subm_id(subm_id)
        ans = self._cache_call(self.pcms.get_compile_error, task, attempt)
        if ans == None: raise IndexError
        return ans
    def submission_source(self, subm_id):
        task, attempt = self._decode_subm_id(subm_id)
        return self._cache_call(self.pcms.get_source, task, attempt)
    def compiler_list(self, task_id):
        tasks, langs, jp, vs = self._cache_call(self.pcms.get_submit)
        return [bjtypes.compiler_t(i + 1, j, k) for i, (j, k) in enumerate(sorted(langs.items())) if j in jp[tasks[task_id]]]
    def submission_stats(self, subm_id):
        task, attempt = self._decode_subm_id(subm_id)
        ans = {}
        score = self.submission_score(subm_id)
        if score != None: ans['score'] = score
        proto = self._cache_call(self.pcms.get_protocol, task, attempt)
        if proto == None:
            raise BruteError("Failed to fetch testing protocol.")
        group_scores = []
        passed = 0
        failed = 0
        for i in proto:
            if 'head group-score' in i[1]:
                score = int(i[1]['head group-score'].split(' = ', 1)[1].split('<', 1)[0])
                group_scores.append(score)
            if 'outcome' not in i[1]: continue
            if i[1]['outcome'] in ('Accepted', 'OK'): passed += 1
            else: failed += 1
        if passed + failed != 0:
            ans['tests'] = {}
            ans['tests']['total'] = passed + failed
            ans['tests']['success'] = passed
            ans['tests']['fail'] = failed
        if group_scores: ans['group_scores'] = group_scores
        return (ans, '')
    def download_file(self, *args):
        raise BruteError("STUB")
    def do_action(self, *args):
        raise BruteError("Not implemented on PCMS")
    def contest_info(self):
        props = self._cache_call(self.pcms.get_info)
        data1 = {}
        if 'Status' in props and '<script type="text/javascript">' in props['Status']:
            script = props['Status'].split('<script type="text/javascript">', 1)[1].split('</script>', 1)[0].strip()
            if script.startswith('clock.init('):
                qq = ast.literal_eval(script[10:-1]) # not a valid JSON
                if len(qq) == 5 and qq[2] == 'RUNNING':
                    data1['contest_time'] = qq[3] / 1000
                    data1['contest_duration'] = qq[4] / 1000
        datas = {k: html.unescape(v) for k, v in props.items() if '<' not in v}
        return ('', datas, data1)
    def problem_info(self, task_id):
        html, base = self._cache_call(self.pcms.get_links)
        return ({}, html2md.html2md(html, None, base))
    def _get_clars(self):
        tasks, clars, vs = self._cache_call(self.pcms.get_clars)
        self._clars = list(clars)
        return tasks, clars, vs
    def clar_list(self):
        self._get_clars()
        self._messages = [j for i, j in self._cache_call(self.pcms.get_messages) if i == 'msg']
        data = [(i * 2, j[1]['text'].split('.', 1)[0]+': '+j[1]['text pre'].replace('\r', '').replace('\n', ' ')+': '+j[1]['type']) for i, j in enumerate(reversed(self._clars))]
        data += [(i * 2 + 1, j) for i, j in enumerate(reversed(self._messages))]
        for x in data:
            if x[0] not in self._user_clars_set:
                self._user_clars_set.add(x[0])
                self._user_clars.append(x)
        return [bjtypes.clar_t(i[0], i[1]) for i in reversed(self._user_clars)]
    def submit_clar(self, task, subject, text):
        tasks, clars, vs = self._get_clars()
        #clars = list: type, text, 'text pre', type, 'answer pre'
        try: task = tasks[task]
        except IndexError: pass
        try: self.pcms.submit_clar(task, subject, text, vs)
        except AssertionError: raise BruteError("Failed to submit clar")
        with self.cache_lock: self.stop_caching()
    def read_clar(self, id):
        self._get_clars()
        id, kind = divmod(id, 2)
        if kind == 0:
            return self._clars[-1-id][1]['answer pre']
        else:
            return self._messages[-1-id]
    def scoreboard(self):
        ans = []
        for i in self._cache_call(self.pcms.monitor)[1]:
            ans.append(({'name': i[0]['party']}, []))
            for j in i[1]:
                q = {}
                if j[1] and j[1][0] in ('+', '-'):
                    try: q['attempts'] = int(j[1][0]+'0'+j[1][1:])
                    except (TypeError, ValueError): pass
                else:
                    try: q['score'] = int(j[1])
                    except (TypeError, ValueError): pass
                if j[2]:
                    try:
                        a, b = j[2].split(':')
                        q['penalty'] = 60 * int(a) + int(b)
                    except (TypeError, ValueError): pass
                q['flags'] = list(j[0])
                ans[-1][1].append(q)
        return ans
    def stop_caching(self):
        self._call_cache.clear()
