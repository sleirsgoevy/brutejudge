def get_urls(main_url):
    return {
        'summary': main_url + '&action=137',
        'submissions': main_url + '&action=140&all_runs=1',
        'protocol': main_url + '&action=37&run_id={run_id}',
        'source': main_url + '&action=91&run_id={run_id}',
        'submission': main_url + '&action=139&prob_id={prob_id}',
        'submit': main_url.split('?')[0],
        'start_virtual': main_url + '&action=144',
        'sid': main_url.split("SID=")[-1].split("&")[0],
    }
