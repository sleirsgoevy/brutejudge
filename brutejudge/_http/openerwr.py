import urllib.request

class OpenerWrapper:
    def __init__(self, o):
        object.__setattr__(self, '_real_opener', o)
    @classmethod
    def _from_pickled(self, cookies):
        import http.cookiejar
        x = http.cookiejar.CookieJar()
        for i in cookies: x.set_cookie(i)
        return OpenerWrapper(urllib.request.build_opener(urllib.request.HTTPCookieProcessor(x)))
    def __reduce__(self):
        return (self._from_pickled, (list([i for i in self._real_opener.handlers if isinstance(i, urllib.request.HTTPCookieProcessor)][0].cookiejar),))
    def __getattr__(self, attr):
        return getattr(self._real_opener, attr)
    def __setattr__(self, attr, val):
        setattr(self._real_opener, attr, val)
    def __delattr__(self, attr):
        delattr(self._real_opener, attr)
