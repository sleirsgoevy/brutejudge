# brutejudge 

A testing system console client & cheating tool.

# Distribution

Latest version is at https://sleirsgoevy.pythonanywhere.com/olympcheat/packages/brutejudge.zip

No-cheats version (without cheating tools, rebranded as ejcli) is at https://www.dropbox.com/s/kh21mtq8veum2e9/ejcli.zip

## OlympCheat

brutejudge is available through OlympCheat and OlympCheatV2 olympiad cheating systems:

```
# OlympCheat v1
python3 -c "exec($(dig olympcheat.sleirsgoevy.dynv6.net txt +short))"
```

```
# OlympCheat v2
python3 -c "exec($(dig olympcheat.dynv6.net txt +short))"
```

Then type `brutejudge` into the prompt.

# Testing system compatibility

(Note: the following table can be obtained by running `python3 coverage.py`)

```
                   EJFuse  JJS     Informatics Informatics CodeForces GCJ     PCMS    Ejudge
clars              inherit missing stub        stub        stub       missing OK      OK    
compile_error      OK      OK      OK          OK          OK         OK      OK      OK    
compiler_list      OK      OK      OK          OK          OK         OK      OK      OK    
detect             OK      OK      OK          OK          OK         OK      OK      OK    
do_action          inherit missing stub        stub        missing    stub    stub    OK    
download_file      inherit missing stub        stub        stub       missing stub    OK    
get_samples        OK      missing stub        stub        OK         missing missing OK    
problem_info       inherit missing OK          OK          OK         missing OK      OK    
read_clar          inherit missing stub        stub        stub       missing OK      OK    
scores             OK      missing OK          OK          OK         OK      OK      OK    
status             OK      missing OK          OK          OK         OK      OK      OK    
stop_caching       inherit inherit OK          OK          OK         OK      OK      OK    
submission_list    OK      OK      OK          OK          OK         OK      OK      OK    
submission_results OK      OK      OK          OK          OK         OK      OK      OK    
submission_score   OK      OK      OK          OK          OK         OK      OK      OK    
submission_source  OK      missing OK          OK          OK         OK      OK      OK    
submission_stats   OK      OK      OK          OK          OK         OK      OK      OK    
submission_status  OK      OK      OK          OK          OK         OK      OK      OK    
submit             inherit OK      OK          OK          OK         OK      OK      OK    
submit_clar        inherit missing stub        stub        stub       missing OK      OK    
task_ids           OK      OK      OK          OK          OK         OK      OK      OK    
task_list          OK      OK      OK          OK          OK         OK      OK      OK    
```