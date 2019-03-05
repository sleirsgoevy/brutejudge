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
         'summary': main_url + '/view-problem-summary/' + sid,
         'submissions': main_url + '/view-submissions/' + sid + '?all_runs=1',
         'protocol': main_url + '/view-report/' + sid + '?run_id={run_id}',
         'source': main_url + '/download-run/' + sid + '?run_id={run_id}',
         'submission': main_url + '/view-problem-submit/' + sid + '?prob_id={prob_id}',
         'submit': main_url,
         'sid': sid[1:]
    }
