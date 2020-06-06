# brutejudge 

A testing system console client & cheating tool.

# Installation

To install brutejudge, run `python3 setup.py install`. brutejudge only supports Python 3.

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
                   AggressiveCacheBackend EJFuse  JJS     Informatics Informatics CodeForces GCJ     PCMS    Ejudge 
clars              missing                inherit missing stub        stub        stub       stub    OK      OK     
compile_error      OK                     OK      OK      OK          OK          OK         OK      OK      OK     
compiler_list      OK                     OK      OK      OK          OK          OK         OK      OK      OK     
contest_info       missing                OK      OK      OK          OK          missing    OK      OK      OK     
contest_list       OK                     inherit OK      inherit     inherit     inherit    OK      inherit OK     
detect             OK                     OK      OK      OK          OK          OK         OK      OK      OK     
do_action          OK                     inherit missing stub        OK          missing    stub    stub    OK     
download_file      missing                inherit missing stub        stub        stub       missing stub    OK     
get_samples        missing                OK      OK      stub        stub        OK         missing missing OK     
login_type         OK                     inherit OK      inherit     inherit     inherit    OK      inherit inherit
problem_info       OK                     inherit missing OK          OK          OK         OK      OK      OK     
read_clar          OK                     inherit missing stub        stub        stub       missing OK      OK     
scoreboard         missing                inherit OK      stub        stub        OK         missing OK      OK     
scores             missing                OK      OK      OK          OK          OK         OK      OK      OK     
status             missing                OK      OK      OK          OK          OK         OK      OK      OK     
stop_caching       missing                inherit OK      OK          OK          OK         OK      OK      OK     
submission_list    missing                OK      OK      OK          OK          OK         OK      OK      OK     
submission_results OK                     OK      OK      OK          OK          OK         OK      OK      OK     
submission_score   OK                     OK      OK      OK          OK          OK         OK      OK      OK     
submission_source  OK                     OK      OK      OK          OK          OK         OK      OK      OK     
submission_stats   OK                     OK      OK      OK          OK          OK         OK      OK      OK     
submission_status  OK                     OK      OK      OK          OK          OK         OK      OK      OK     
submit             missing                inherit OK      OK          OK          OK         OK      OK      OK     
submit_clar        missing                inherit missing stub        stub        stub       missing OK      OK     
task_ids           OK                     OK      OK      OK          OK          OK         OK      OK      OK     
task_list          OK                     OK      OK      OK          OK          OK         OK      OK      OK     
```
