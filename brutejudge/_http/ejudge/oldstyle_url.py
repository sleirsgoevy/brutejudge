from .action_ids import data as _raw_action_ids
from ...error import BruteError
from . import get

def _parse_action_ids(raw_action_ids):
    action_ids = {}
    current_version = ()
    current_actions = []
    for l in raw_action_ids.split('\n'):
        l = l.split(' ')
        assert l
        l.append(None)
        l = iter(l)
        cmd = next(l)
        while cmd != None:
            if cmd == '-':
                start = int(next(l))
                cnt = int(next(l))
                del current_actions[start:start+cnt]
                cmd = next(l)
            elif cmd == '+':
                start = int(next(l))
                cur = next(l)
                chk = []
                while cur not in ('+', '-', '!', None):
                    chk.append(cur)
                    cur = next(l)
                current_actions[start:start] = chk
                cmd = cur
            elif cmd == '!':
                current_version = tuple(map(int, next(l).split('.')))
                cmd = next(l)
        if current_version not in action_ids: action_ids[current_version] = []
        action_ids[current_version].append([None if i == '?' else i for i in current_actions])
    return action_ids

action_ids = _parse_action_ids(_raw_action_ids)
del _parse_action_ids, _raw_action_ids

def get_actions(version):
    version = tuple(map(int, version.split('.')))
    # first try the exact version. assume that the release tarball is being used, thus use the first known commit that declares itself that version
    try: return action_ids[version][0]
    except KeyError:
        # now try the minimum version before specified
        try: version = max(i for i in action_ids if i < version)
        except ValueError:
            # this is ejudge from 2006 or earlier. are there any still in use?
            raise BruteError("ejudge version too old")
        else:
            # our version is bigger, so any changes in the older one must've propagated to ours
            return action_ids[version][-1]

def get_urls(main_url, headers, version):
    actions = get_actions(version)
    # huawei's ejudge has task ids shifted by 2. doing our best to detect that...
    if actions[actions.index('NEW_SRV_ACTION_VIEW_CLAR_SUBMIT') - 2] == 'NEW_SRV_ACTION_VIEW_PROBLEM_SUBMIT':
        code, headers, data = get(main_url + '&action=' + str(actions.index('NEW_SRV_ACTION_VIEW_CLAR_SUBMIT')), headers)
        if code == 200:
            data = data.decode('utf-8', 'replace')
            if '<select name="prob_id">' in data and '<input type="text" name="subject"' not in data:
                # looks like this is a problem selection page...
                actions[3:3] = (None, None)
    action_to_idx = dict(map(reversed, enumerate(actions)))
    try: del action_to_idx[None]
    except KeyError: pass
    ans = {
        'contest_list': main_url.split('?', 1)[0][:-6]+'register',
        'contest_info': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_MAIN_PAGE']),
        'summary': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIEW_PROBLEM_SUMMARY']),
        'submissions': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIEW_SUBMISSIONS']) + '&all_runs=1',
        'protocol': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIEW_REPORT']) + '&run_id={run_id}',
        'task_select': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIEW_PROBLEM_SUBMIT']),
        'submission': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIEW_PROBLEM_SUBMIT']) + '&prob_id={prob_id}',
        'submit': main_url.split('?')[0],
        'standings': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_STANDINGS']),
        'start_virtual': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIRTUAL_START']),
        'stop_virtual': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIRTUAL_STOP']),
        'download_file': main_url + '&prob_id={prob_id}&action=' + str(action_to_idx['NEW_SRV_ACTION_GET_FILE']) + '&file={filename}',
        'clars': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIEW_CLARS']) + '&all_clars=1',
        'read_clar': main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_VIEW_CLAR']) + '&clar_id={clar_id}',
        'sid': main_url.split("SID=")[-1].split("&")[0],
        'change_password': 'action_' + str(action_to_idx['NEW_SRV_ACTION_CHANGE_PASSWORD']),
        'submit_run': 'action_' + str(action_to_idx['NEW_SRV_ACTION_SUBMIT_RUN']),
        'submit_clar': 'action_' + str(action_to_idx['NEW_SRV_ACTION_SUBMIT_CLAR']),
    }
    try: ans['source'] = main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_DOWNLOAD_RUN']) + '&run_id={run_id}'
    except KeyError: ans['source'] = main_url + '&action=' + str(action_to_idx['NEW_SRV_ACTION_PRIV_DOWNLOAD_RUN']) + '&run_id={run_id}'
    return ans
