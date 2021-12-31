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

# API documentation

[API.md](https://github.com/sleirsgoevy/brutejudge/blob/master/API.md)

## Testing system compatibility

(Note: the following table can be obtained by running `python3 coverage.py`)

```
                    AggressiveCacheBackend EJFuse  JJS     Informatics CodeForces GCJ     PCMS    Ejudge 
change_password     missing                inherit missing inherit     missing    missing missing OK     
clar_list           missing                inherit missing stub        stub       missing OK      OK     
compile_error       OK                     OK      OK      OK          OK         OK      OK      OK     
compiler_list       OK                     OK      OK      OK          OK         OK      OK      OK     
contest_info        missing                OK      OK      OK          OK         OK      OK      OK     
contest_list        OK                     inherit OK      inherit     OK         OK      inherit OK     
detect              OK                     OK      OK      OK          OK         OK      OK      OK     
do_action           OK                     inherit missing OK          missing    stub    stub    OK     
download_file       missing                inherit missing stub        stub       missing stub    OK     
get_samples         missing                OK      OK      stub        OK         missing missing OK     
locales             missing                missing missing missing     OK         missing missing missing
login_type          OK                     inherit OK      inherit     inherit    OK      inherit inherit
problem_info        OK                     inherit missing OK          OK         OK      OK      OK     
read_clar           OK                     inherit missing stub        stub       missing OK      OK     
scoreboard          missing                inherit OK      stub        OK         missing OK      OK     
scores              missing                OK      OK      OK          OK         OK      OK      OK     
set_locale          missing                missing missing missing     OK         missing missing missing
status              missing                OK      OK      OK          OK         OK      OK      OK     
stop_caching        missing                inherit OK      OK          OK         OK      OK      OK     
submission_protocol OK                     OK      OK      OK          OK         OK      OK      OK     
submission_score    missing                OK      missing missing     missing    missing missing missing
submission_source   OK                     OK      OK      OK          OK         OK      OK      OK     
submission_stats    OK                     OK      OK      OK          OK         OK      OK      OK     
submission_status   missing                OK      missing missing     missing    missing missing missing
submissions         missing                OK      OK      OK          OK         OK      OK      OK     
submit_clar         missing                inherit missing stub        stub       missing OK      OK     
submit_solution     missing                inherit OK      OK          OK         OK      OK      OK     
tasks               OK                     OK      OK      OK          OK         OK      OK      OK     
```
