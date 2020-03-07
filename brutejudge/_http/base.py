import threading

class CacheContext:
    def __init__(self, be):
        self.be = be
    def __enter__(self):
        with self.be.cache_lock:
            self.be.caching += 1
    def __exit__(self, *args):
        with self.be.cache_lock:
            self.be.caching -= 1
            if not self.be.caching: self.be.stop_caching()

class LockWrapper:
    def __init__(self):
        self.lock = threading.RLock()
    def __enter__(self):
        self.lock.acquire()
    def __exit__(self, *args):
        self.lock.release()
    def __reduce__(self):
        return (LockWrapper, ())

class Backend:
    def __init__(self):
        self.cache_lock = LockWrapper()
        self.caching = 0
    def may_cache(self):
        return CacheContext(self)
    def stop_caching(self): pass
    @staticmethod
    def login_type(url):
        return ['login', 'pass']
    def contest_list(self):
        return []
