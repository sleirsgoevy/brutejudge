import html
from . import Ejudge, get, post
from ...error import BruteError

class InfOpen(Ejudge):
    @staticmethod
    def detect(url):
        url = url.replace('http://', 'https://') + '/'
        return url.startswith('https://inf-open.ru/')
    def __init__(self, url, login, password):
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        code, headers, data = post('https://inf-open.ru/login/', {'username': login, 'password': password}, {'Content-Type': 'application/x-www-form-urlencoded'})
        if code != 302 or headers['Location'] != '/':
            raise BruteError("Login failed")
        cookie = next(i for i in headers['Set-Cookie'] if i.startswith('user_session=')).split(';', 1)[0]
        code, headers, page = get(url, {'Cookie': cookie})
        get('https://inf-open.ru/logout', {'Cookie': cookie})
        if code != 200:
            raise BruteError("Contest not found")
        page = page.decode('utf-8', 'replace')
        if '<form method="post" action="https://inf-open.ru/ej/client" ' not in page:
            raise BruteError("Not a contest page")
        form_fields = {}
        for i in page.split('<form method="post" action="https://inf-open.ru/ej/client" ', 1)[1].split('>', 1)[1].split('</form>', 1)[0].split('<input ')[1:]:
            name = html.unescape(i.split(' name="', 1)[1].split('"', 1)[0])
            value = html.unescape(i.split(' value="', 1)[1].split('"', 1)[0]) if ' value="' in i else ''
            form_fields[name] = value
        Ejudge.__init__(self, 'https://inf-open.ru/ej/client?contest_id='+str(int(form_fields['contest_id'])), form_fields['login'], form_fields['password'])
    def scoreboard(self):
        ans = Ejudge.scoreboard(self)
        if not ans:
            code, headers, data = get('https://inf-open.ru/standings.html')
            if code != 200:
                raise BruteError("Failed to fetch scoreboard.")
            return self._parse_scoreboard(data)
