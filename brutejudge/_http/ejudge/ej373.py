def get_urls(main_url):
    if '?SID=' in main_url:
        main_url, sid = main_url.split('?SID=')
        sid = 'S' + sid
    else:
        main_url, sid = main_url.rsplit('/', 1)
        sid = sid.split('?')[0]
    if main_url.endswith('/main-page'):
        main_url = main_url[:-10]
    if main_url.endswith('/register'):
        main_url = main_url[:-9] + '/user'
    return {
        'contest_list': main_url[:-5]+'/register',
        'contest_info': main_url + '/main-page/' + sid,
        'summary': main_url + '/view-problem-summary/' + sid,
        'submissions': main_url + '/view-submissions/' + sid + '?all_runs=1',
        'protocol': main_url + '/view-report/' + sid + '?run_id={run_id}',
        'source': main_url + '/download-run/' + sid + '?run_id={run_id}',
        'submission': main_url + '/view-problem-submit/' + sid + '?prob_id={prob_id}',
        'submit': main_url,
        'standings': main_url + '/standings/' + sid,
        'start_virtual': main_url + '?SID=' + sid[1:] + '&action=144',
        'stop_virtual': main_url + '?SID=' + sid[1:] + '&action=145',
        'download_file': main_url + '?SID=' + sid[1:] + '&prob_id={prob_id}&action=194&file={filename}',
        'clars': main_url + '/view-clars/' + sid + '?all_clars=1',
        'read_clar': main_url + '/view-clar/' + sid + '?clar_id={clar_id}',
        'sid': sid[1:]
    }
