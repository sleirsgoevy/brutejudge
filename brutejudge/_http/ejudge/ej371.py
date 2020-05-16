def get_urls(main_url):
    return {
        'contest_list': main_url.split('?', 1)[0][:-6]+'register',
        'contest_info': main_url + '&action=2',
        'summary': main_url + '&action=137',
        'submissions': main_url + '&action=140&all_runs=1',
        'protocol': main_url + '&action=37&run_id={run_id}',
        'source': main_url + '&action=91&run_id={run_id}',
        'submission': main_url + '&action=139&prob_id={prob_id}',
        'submit': main_url.split('?')[0],
        'standings': main_url + '&action=94',
        'start_virtual': main_url + '&action=144',
        'stop_virtual': main_url + '&action=145',
        'download_file': main_url + '&prob_id={prob_id}&action=194&file={filename}',
        'clars': main_url + '&action=142&all_clars=1',
        'read_clar': main_url + '&action=39&clar_id={clar_id}',
        'sid': main_url.split("SID=")[-1].split("&")[0],
    }
