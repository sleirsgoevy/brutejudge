class AggressiveCacheBackend:
    @staticmethod
    def detect(url):
        return url.startswith('cached:')
    def __init__(self, url, login, password, **kwargs):
        import brutejudge.http
        self.parent = brutejudge.http.login(url[7:], login, password, **kwargs)[0]
        self.task_list_cache = None
        self.problem_info_cache = {}
        self.compiler_list_cache = {}
        self.submission_results_cache = {}
        self.submission_status_cache = {}
        self.submission_source_cache = {}
        self.clars_cache = {}
    def task_list(self):
        q = self.task_list_cache
        if q != None: return q[0]
        with self.parent.may_cache():
            self.task_list_cache = (self.parent.task_list(), self.parent.task_ids())
        return self.task_list_cache[0]
    def _submission_results(self, id):
        try: return self.submission_results_cache[id]
        except KeyError: pass
        with self.parent.may_cache():
            q = (
                self.parent.submission_status(id),
                self.parent.submission_score(id),
                self.parent.compile_error(id),
                self.parent.submission_results(id),
                self.parent.submission_stats(id),
            )
        import brutejudge.commands.astatus
        if not brutejudge.commands.astatus.still_running(q[0]): self.submission_results_cache[id] = q
        return q
    def submission_results(self, id):
        return self._submission_results(id)[3]
    def task_ids(self):
        q = self.task_list_cache
        if q != None: return q[1]
        with self.parent.may_cache():
            self.task_list_cache = (self.parent.task_list(), self.parent.task_ids())
        return self.task_list_cache[1]
    def compile_error(self, id):
        return self._submission_results(id)[2]
    def submission_status(self, id):
        return self._submission_results(id)[0] 
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
    def submission_score(self, id):
        return self._submission_results(id)[1]
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
