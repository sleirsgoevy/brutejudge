import urllib.parse, types, sys
from ..error import BruteError

class FileBackend:
    @staticmethod
    def detect(url):
        return url.startswith('file:')
    @staticmethod
    def _import(url):
        path = url[5:].split('#', 1)[0]
        if '?' in path:
            path, args = path.split('?', 1)
            args = dict(urllib.parse.parse_qsl(args))
        else:
            args = {}
        path = urllib.parse.unquote(path)
        cls = args.get('class', 'TheBackend')
        try: file = open(path)
        except IOError:
            raise BruteError("File not found.")
        mod0 = types.ModuleType('file:'+path)
        mod = sys.modules.setdefault('file:'+path, mod0)
        if mod is mod0:
            try: exec(compile(file.read(), path, 'exec'), mod.__dict__, mod.__dict__)
            except:
                try: del sys.modules['file:'+path]
                except KeyError: pass
                raise
        if not hasattr(mod, cls):
            raise BruteError("Backend class not found.")
        return getattr(mod, cls)
    @classmethod
    def login_type(cls, url):
        return cls._import(url).login_type(url)
    def __new__(self, url, *args0, **kwds0):
        return self._import(url)(url, *args0, **kwds0)
