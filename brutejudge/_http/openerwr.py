import urllib.request

class OpenerWrapper:
    def __init__(self, o):
        object.__setattr__(self, '_real_opener', o)
    @classmethod
    def with_cookies(self, cookies=[], addheaders=[]):
        if cookies is not None:
            import http.cookiejar
            x = http.cookiejar.CookieJar()
            for i in cookies: x.set_cookie(i)
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(x))
        else:
            op = urllib.request.build_opener()
        op.addheaders = addheaders
        return self(op)
    def __reduce__(self):
        try: cookies = list([i for i in self._real_opener.handlers if isinstance(i, urllib.request.HTTPCookieProcessor)][0].cookiejar)
        except IndexError: cookies = None
        return (self.with_cookies, (cookies, self.addheaders))
    def __getattr__(self, attr):
        return getattr(self._real_opener, attr)
    def __setattr__(self, attr, val):
        setattr(self._real_opener, attr, val)
    def __delattr__(self, attr):
        delattr(self._real_opener, attr)
