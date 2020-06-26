class AggressiveCacheBackend:
    @staticmethod
    def detect(url):
        return url.startswith('cached:')
    @staticmethod
    def login_type(url):
        import brutejudge.http
        return brutejudge.http.login_type(url[7:])
    def __init__(self, url, login, password, **kwargs):
        import brutejudge.http
        self.parent = brutejudge.http.login(url[7:], login, password, **kwargs)[0]
        self.task_list_cache = None
        self.problem_info_cache = {}
        self.compiler_list_cache = {}
        self.submission_protocol_cache = {}
        self.submission_status_cache = {}
        self.submission_source_cache = {}
        self.compile_error_cache = {}
        self.clars_cache = {}
    def tasks(self):
        q = self.task_list_cache
        if q != None: return q
        self.task_list_cache = self.parent.tasks()
        return self.task_list_cache
    def submission_protocol(self, id):
        try: return self.submission_protocol_cache[id]
        except KeyError: pass
        q = self.parent.submission_protocol(id)
        import brutejudge.commands.astatus
        if q: self.submission_protocol_cache[id] = q
        return q
    def compile_error(self, id):
        try: return self.compile_error_cache[id]
        except KeyError: pass
        ans = self.parent.compile_error(id)
        if ans: self.submission_protocol_cache[id] = ans
        return ans
    def submission_source(self, id):
        try: return self.submission_source_cache[id]
        except KeyError: pass
        self.submission_source_cache[id] = self.parent.submission_source(id)
        return self.submission_source_cache[id]
    def do_action(self, id, *args):
        if id == 'flush_cache':
            self.task_list_cache = None
            self.problem_info_cache.clear()
            self.compiler_list_cache.clear()
            self.submission_results_cache.clear()
            self.submission_status_cache.clear()
            self.submission_source_cache.clear()
            self.clars_cache.clear()
        else:
            self.parent.do_action(id, *args)
    def compiler_list(self, prob_id):
        try: return self.compiler_list_cache[prob_id]
        except KeyError: pass
        self.compiler_list_cache[prob_id] = self.parent.compiler_list(prob_id)
        return self.compiler_list_cache[prob_id]
    def submission_stats(self, subm_id):
        return self._submission_results(subm_id)[4]
    def problem_info(self, id):
        try: return self.problem_info_cache[id]
        except KeyError: pass
        self.problem_info_cache[id] = self.parent.problem_info(id)
        return self.problem_info_cache[id]
    def read_clar(self, id):
        try: return self.clars_cache[id]
        except KeyError: pass
        self.clars_cache[id] = self.parent.read_clar(id)
        return self.clars_cache[id]
    def contest_list(self):
        if isinstance(self, str):
            import brutejudge.http
            return brutejudge.http.contest_list(self[7:])
        else:
            return self.parent.contest_list()
    def __getattr__(self, attr):
        return getattr(self.parent, attr)
