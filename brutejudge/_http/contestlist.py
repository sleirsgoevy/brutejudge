import urllib.parse
from brutejudge._http.base import Backend
from brutejudge.error import BruteError

class ContestList(Backend):
    @staticmethod
    def detect(url):
        return url.startswith('contestlist:?')
    @staticmethod
    def login_type(url):
        return ['contest_list']
    def __init__(self, login, password):
        raise BruteError("contestlist cannot be directly logged into")
    def contest_list(self):
        assert isinstance(self, str)
        if len(self) == 13: return []
        return [tuple(map(urllib.parse.unquote, i.split('=', 1))) + ({},) for i in self[13:].split('&')]
