# brutejudge public API

The public API is fully described within this document. Everything that is not described here should be considered private.

**ejcli/brutejudge difference**: these are essentially the same from the point of public API. Client applications should try to import both of these modules.

## Exception policy

All functions described below **should** raise `brutejudge.error.BruteError` (`ejcli.error.EJError` in ejcli) on error conditions, unless otherwise specified. Other exceptions can also be raised if there is an unexpected error.

## `brutejudge.http`

The `brutejudge.http` module contains the majority of functions for interacting with testing system.

### `login(login_url, login, password, **params) -> (url, cookie)`

Logs into the testing system specified by `login_url`.

`login` and `password` should be the user's credentials, as specified in the login form. If a custom authorization scheme is used (see below), additional parameters must be specified as keyword arguments. In this case `login` and `password` should be set to None, or contain the actual login and password if the authorization scheme being used has such concepts.

This function returns a tuple of two values, `url` and `cookie`. Client applications should treat these parameters as opaque references; the only thing that is guaranteed is that `bool(url) == bool(cookie) == True`.

### `login_type(login_url) -> [str]`

This function returns a list of strings that specify various features supported by the testing system at `login_url`. Client applications should ignore any string that they can't understand.

* `"login"`. The client should provide username (login) to the `login` function. This parameter is ignored if `"login"` is not present and should pe passed as None.
* `"pass"`. Same semantics as `"login"` but for password.
* `"contest_list"`. If specified, `login_url` refers to a contest selection screen. The client should query the contest list via `contest_list` (see below) and not call `login` on this URL.
* `"goauth:"+...`. The testing system supports logging in via Google OAuth. To be documented.

A special case of `[]` means that `login(login_url, None, None)` will succeed and no explicit authentication is required.

### `contest_list(url, cookie) -> [(name, url, metadata)]`

This function can be called in two ways:

* if `cookie` is None, url is treated like `login_url`.
* if `cookie` is not None, `(url, cookie)` must be a valid session.

This function returns a list of subcontests of the given `login_url`. `name` is the display name of the subcontest, `url` is the `login_url` for the subcontest, and `metadata` is a dictionary containing optional metadata.

All the following functions require `(url, cookie)` to be a valid session. On error they either raise an exception or return a valid "empty" result. `subm_id` **must** be an integer when passed as an argument, and can be an integer or a string representing a decimal number when returned from an API call. Clients should check for both cases.

### `task_list(url, cookie) -> [str]`

### `task_ids(url, cookie) -> [int]`

These functions return the list of problems available. `task_list` returns the user-readable short name while `task_ids` returns integer problem identifiers. These lists are synchronized unless contest settings changed between the two calls.

### `submission_list(url, cookie) -> ([subm_id], [str])`

This function returns a tuple two lists. The first list contains the list of global submission ids for all submissions. The second list contains the list of task short names, as returned by `task_list`, for all submissions.

This operation is atomic, i.e. the two lists are always synchronized and represent the list of all submissions last-to-first.

### `submission_results(url, cookie, subm_id) -> ([str], [str])`

This function returns the testing protocol for the specified submission. The first list contains a list of per-test statuses in the logical test order. Statuses are written in natural English (i.e. `Wrong answer`, not `WRONG_ANSWER` or `Неправильный ответ`). The second list contains a list of per-test statistic strings (these **should** be `"%0.3f"%elapsed_cpu_time_in_seconds`). The lists are guaranteed to be synchronized.

### `submit(url, cookie, task_id, lang_id, code)`

Submit a solution to `task_id` in language `lang_id`. `task_id` should be an index into `task_list`, not a value from `task_ids`. `lang_id` should be a valid compiler ID (see `compiler_list`). `code` should be either bytes or str.

The return value of this function is unspecified and should be ignored. However a successful return does not mean that the attempt has been submitted; the client should check that the new submission actually appeared on `submission_list`.

### `status(url, cookie) -> dict`

Returns a dictionary containing per-problem statuses. The result is either a dict or a dict-like object (i.e. `collections.OrderedDict`), where key is a problem short name (as in `task_list`), and value is either the status string in natural English, or None.

### `scores(url, cookie) -> dict`

This function is similar to the above, except that value is either an `int` with the contestant's score for the problem, or None.

### `compile_error(url, cookie, subm_id) -> str`

This function fetches the compiler output for the specified submission, if possible. The return value is either a Unicode string, or None if the compiler output is not available.

### `submission_status(url, cookie, subm_id) -> str`

This function returns the judge verdict for the specified submission. The return value is either the verdict in natural English, or None.

### `submission_source(url, cookie, subm_id) -> bytes`

This function returns the source code for the specified submission, or None if one is not available.

Note: the result is **not** guaranteed to be exactly the same as passed to `submit` (e.g. the testing system may have reencoded the solution into a different encoding).

### `compiler_list(url, cookie, task_id) -> [(int, str, str)]`

This function returns the list of allowed languages for a specific problem. `task_id` should be one of the values returned by `task_ids`. Elements of the returned list consist of the numeric `lang_id`, short name (e.g. `gcc`), and long name (e.g. `GNU C Compiler`).

### `submission_stats(url, cookie, subm_id) -> dict`

Returns a dictionary with statistics on the specified submission. Information is provided on a best-effort basis, e.g. no key is guaranteed to be present.

* `stats["tests"]["total"]`. The total number of tests the submission has been tested on.
* `stats["tests"]["success"]`. The total number of tests that have been passed.
* `stats["tests"]["fail"]`. The total number of tests that have been failed.
* `stats["score"]`. The total score for the submission. Note: use `submission_score` if this field is not available.
* `stats["group_scores"]`. A list of per-group scores gained on each test group.

### `contest_info(url, cookie) -> (str, dict, dict)`

This function returns generic info about the contest. The return values are:

* description of the contest, as specified by administrators
* contest-specific data (human-readable key-value pairs)
* contest-specific data (machine-readable key-value pairs)

Machine-readable data is provided on a best-effort basis (see above).

* `data["contest_start"]`. Contest start time in seconds since the Epoch.
* `data["contest_end"]`. Contest end time in seconds since the Epoch.
* `data["server_time"]`. Server time in seconds since the Epoch.
* `data["contest_time"]`. Server time in seconds since the contest start.
* `data["contest_duration"]`. Contest duration in seconds.

Note: clients should **not** assume that the timezone is UTC or the local system's timezone.

### `problem_info(url, cookie, task_id) -> (dict, str)`

This function returns problem-specific information in human-readable form. The first return value is a dict of human-readable key-value pairs, and the second is a Markdown description of the problem (usually the problem statement).

`task_id` is as returned from `task_ids`.

### `download_file(url, cookie, task_id, filename) -> bytes`

This function is used to download problem-specific assets from the testing system. If the Markdown description contains a link that looks like `[click here](file filename.bin)`, then the client should call this with the proper `task_id` and with `filename="filename.bin"`.

`task_id` is as returned from `task_ids`.

### `submission_score(url, cookie, subm_id) -> int`

This function returns the submission's score as decided by the judge, or None if the information if not available.

### `clars(url, cookie) -> ([int], [str])`

This function returns the list of contestant-to-jury and jury-to-contestant messages, also known as clarification requests (clars). The first list contains global numeric identifiers (`clar_id`) in the last-to-first order. The second list contains clars' subjects in the same order. The two lists are guaranteed to be synchronized.

This function may raise an exception if clarification requests are not supported or disabled.

### `submit_clar(url, cookie, task_id, subject, text)`

This function sends a clarification request on the specified task, with the specified subject and body. `task_id` must be as returned from `task_ids`, `subject` and `text` must be Unicode strings. An exception will be thrown if the submission fails.

### `read_clar(url, cookie, clar_id) -> str`

Returns the contents of the specified message as a human-readable string, or None.

Note: this is not necessarily constant. The testing system may do some internal bookkeeping, e.g. mark the message as read.

### `get_samples(url, cookie, subm_id) -> dict`

This function retrieves the test cases that are publicly shown in the protocol. Key is a test number (usually starting from 1), and value is a dictionary with the following keys:

* `"Input"`. Value is the test input as a Unicode string.
* `"Output"`. Value is the solution's output as a Unicode string.
* `"Stderr"`. Value is the solution's error output as a Unicode string.
* `"Correct"`. Value is the correct answer as a Unicode string.
* `"Checker output"`. Value is the checker program output as a Unicode string.

Information is provided on a best-effort basis (see above).

### `scoreboard(url, cookie) -> [(dict, [dict])]`

This function returns the rows of the scoreboard table up-to-down. The row format is as follows:

* The first element is a dict containing contestant metadata (currently the only key here is `"name"`)
* The second element is a list of dicts containing per-problem data for the contastant (currently there are two keys: `"score"` and `"attempts"`, where `"attempts"` is the attempt count as shown in the ACM ICPC scoreboard).

The information is provided on a best-effort basis.

### `may_cache(url, cookie)`

This function is a context manager. When the context manager for a specific session is active in at least one thread, all data retrieved from the testing system is cached client-side. This is useful for saving bandwidth when several subsequent API calls pull the same data internally. The cache is flushed on any call to `submit` or `submit_clar` or when the last thread exits `may_cache`.

## `brutejudge.commands`

### `brutejudge.commands.scoreboard.format_single(meta) -> str`

This function receives the dict with per-problem data (as returned by `scoreboard`) and converts it into a human-readable scoreboard entry (e.g. `100 (+10)`). Clients should use this if they don't need some sophisticated rendering.

### `brutejudge.commands.astatus.still_running(str) -> bool`

This function receives the current submission status (as returned by `submission_status`) and decides whether the submission is still being judged or not.

### `brutejudge.commands.googlelogin.get_auth_token`

To be documented.
