class CacheContext:
    def __init__(self, be):
        self.be = be
    def __enter__(self):
        self.be.caching += 1
    def __exit__(self, *args):
        self.be.caching -= 1
        if not self.be.caching: self.be.stop_caching()

class Backend:
    def __init__(self):
        self.caching = 0
    def may_cache(self):
        return CacheContext(self)
    def stop_caching(self): pass
