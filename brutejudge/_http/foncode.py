import urllib.parse, html, json, time
from brutejudge._http.base import Backend
from brutejudge.error import BruteError
from brutejudge._http.ejudge import get, post
import brutejudge._http.html2md as html2md
import brutejudge._http.types as bjtypes

class FonCode(Backend):
    @staticmethod
    def detect(url):
        return url.startswith('https://foncode.ru/contests/') and url[28:].isnumeric()
    def __init__(self, url, login, password):
        Backend.__init__(self)
        code, headers, data = get('https://foncode.ru/login')
        if code != 200:
            raise BruteError("Failed to fetch login page.")
        token = html.unescape(data.decode('utf-8', 'replace').split('<input type="hidden" name="_token" value="', 1)[1].split('"', 1)[0])
        cookies = [i.split(';', 1)[0] for i in headers['Set-Cookie']]
        code, headers, data = post('https://foncode.ru/login', {'_token': token, 'login': login, 'password': password, 'submit': 'Войти'}, {'Cookie': '; '.join(cookies)})
        if code != 302 or headers['Location'] != 'https://foncode.ru':
            raise BruteError("Login failed.")
        cookies = [i.split(';', 1)[0] for i in headers['Set-Cookie']]
        self.cookie = '; '.join(cookies)
        self.csrf_token, = (urllib.parse.unquote(i[11:]) for i in cookies if i.startswith('XSRF-TOKEN='))
        self.base_path = url
        self._get_cache = {}
    def stop_caching(self):
        self._get_cache.clear()
    def _cache_get(self, path):
        if path.startswith('/'):
            path = self.base_path + path
        with self.cache_lock:
            if path in self._get_cache:
                return self._get_cache[path]
        ans = get(path, {'Cookie': self.cookie})
        with self.cache_lock:
            if self.caching:
                self._get_cache[path] = ans
        return ans
    def _get(self, path, redir=False):
        if path.startswith('/'):
            path = self.base_path + path
        code, headers, data = self._cache_get(path)
        while redir and code in (301, 302):
            path = urllib.parse.urljoin(path, headers['Location'])
            code, headers, data = self._cache_get(path)
        if code != 200:
            raise BruteError("Got an unexpected HTTP code %d on %s"%(code, path))
        return data.decode('utf-8', 'replace')
    def _tasks(self):
        data = self._get('/tasks')
        ans = []
        for i in data.split('<table class="content__table-big">', 1)[1].split('<tr>')[2:]:
            letter = html.unescape(i.split('<td>', 1)[1].split('</td>', 1)[0])
            link = i.split('<td class="content__table-cellbig">', 1)[1].split('</td>', 1)[0].split('</a>', 1)[0]
            url, name = link.split('<a target="_blank" href="', 1)[1].split('">', 1)
            url = html.unescape(url)
            name = html.unescape(name)
            ans.append((letter, name, url))
        return ans
    def tasks(self):
        return [bjtypes.task_t(idx, i, j) for idx, (i, j, k) in enumerate(self._tasks())]
    def submissions(self):
        tasks = {j: i for i, j, k in self._tasks()}
        verdicts = {'Превышено ограничение памяти': 'Memory limit exceeded', 'Неправильный ответ': 'Wrong answer', 'Ошибка исполнения': 'Runtime error', 'Превышено ограничение времени': 'Time limit exceeded'}
        data = self._get('/results')
        headers = [i.split('</th>', 1)[0] for i in data.split('<th>')[1:]]
        ans = []
        idx_id = headers.index('ID')
        idx_taskname = headers.index('Задача')
        idx_verdict = headers.index('Результат')
        idx_test = headers.index('Тест')
        for i in data.split('<tr>')[2:]:
            tds = [j.split('</td>', 1)[0].strip() for j in i.split('<td>')[1:]]
            ans.append(bjtypes.submission_t(int(tds[idx_id]), tasks[tds[idx_taskname]], verdicts.get(tds[idx_verdict], tds[idx_verdict]), None, int(tds[idx_test]) - 1 if tds[idx_test] else None))
        return ans
    def contest_info(self):
        data = self._get('/main')
        return {}, {}, html2md.html2md(data.split('<div class="content__tab content__tab_active" id="tab1">', 1)[1].split('<div class="b-popup notification">', 1)[0])
    def problem_info(self, prob_id):
        return {}, html2md.html2md(self._get(self._tasks()[prob_id][2], True))
