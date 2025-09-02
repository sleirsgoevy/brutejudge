# brutejudge 

A testing system console client & cheating tool.

# Installation

To install brutejudge, run `python3 setup.py install`. brutejudge only supports Python 3.

# Distribution

Latest version is at https://sleirsgoevy.pythonanywhere.com/olympcheat/packages/brutejudge.zip

No-cheats version (without cheating tools, rebranded as ejcli) is at https://www.dropbox.com/s/kh21mtq8veum2e9/ejcli.zip

## OlympCheat

**Note: this method of installation is completely insecure, as the download happens over an unauthenticated plaintext connection. Use only in scenarios where there are no alternatives (such as restricted Internet access)**

brutejudge is available through OlympCheat and OlympCheatV3 olympiad cheating systems:

```
# OlympCheat v1
python3 -c "exec($(dig olympcheat.sleirsgoevy.dynv6.net txt +short))"
```

```
# OlympCheat v3
python3 -c "exec($(dig bmain.olympcheat.dev txt +short))"
```

Then type `brutejudge` into the prompt.

# API documentation

[API.md](https://github.com/sleirsgoevy/brutejudge/blob/master/API.md)

## Testing system compatibility

(Note: the following table can be obtained by running `python3 coverage.py`)

```
                    AggressiveCacheBackend FileBackend EJFuse  CLICS   JJS     Informatics CodeForces GCJ     CupsOnline YaContest InfOpen AtCoder FonCode PCMS    Ejudge 
action_list         OK                     missing     inherit inherit inherit OK          OK         inherit inherit    OK        inherit OK      inherit inherit OK     
change_password     missing                missing     inherit missing missing inherit     missing    missing missing    missing   inherit missing missing missing OK     
clar_list           missing                missing     inherit OK      missing stub        stub       missing missing    OK        inherit OK      missing OK      OK     
compile_error       OK                     missing     OK      missing OK      OK          OK         OK      OK         OK        inherit OK      missing OK      OK     
compiler_list       OK                     missing     OK      OK      OK      OK          OK         OK      OK         OK        inherit OK      missing OK      OK     
contest_info        missing                missing     OK      OK      OK      OK          OK         OK      OK         OK        inherit OK      OK      OK      OK     
contest_list        OK                     missing     inherit OK      OK      inherit     OK         OK      OK         inherit   inherit OK      inherit inherit OK     
detect              OK                     OK          OK      OK      OK      OK          OK         OK      OK         OK        OK      OK      OK      OK      OK     
do_action           OK                     missing     inherit missing missing OK          OK         stub    missing    OK        inherit OK      missing stub    OK     
download_file       missing                missing     inherit missing missing stub        stub       missing missing    missing   inherit missing missing stub    OK     
get_samples         missing                missing     OK      missing OK      stub        OK         missing OK         missing   inherit missing missing missing OK     
locales             missing                missing     missing missing missing missing     OK         missing missing    missing   missing missing missing missing missing
login_type          OK                     missing     inherit OK      OK      inherit     inherit    OK      OK         inherit   inherit inherit inherit inherit inherit
problem_info        OK                     missing     inherit missing missing OK          OK         OK      OK         OK        inherit OK      OK      OK      OK     
read_clar           OK                     missing     inherit OK      missing stub        stub       missing missing    OK        inherit OK      missing OK      OK     
scoreboard          missing                missing     inherit missing OK      stub        OK         missing OK         OK        OK      OK      missing OK      OK     
scores              missing                missing     OK      missing OK      OK          OK         OK      OK         missing   inherit OK      missing OK      OK     
set_locale          missing                missing     missing missing missing missing     OK         missing missing    missing   missing missing missing missing missing
status              missing                missing     OK      missing OK      OK          OK         OK      OK         OK        inherit missing missing OK      OK     
stop_caching        missing                missing     inherit OK      OK      OK          OK         OK      OK         inherit   inherit OK      OK      OK      OK     
submission_protocol OK                     missing     OK      missing OK      OK          OK         OK      OK         OK        inherit OK      missing OK      OK     
submission_score    missing                missing     OK      missing missing missing     missing    missing missing    missing   missing missing missing missing missing
submission_source   OK                     missing     OK      OK      OK      OK          OK         OK      OK         OK        inherit OK      missing OK      OK     
submission_stats    OK                     missing     OK      missing OK      OK          OK         OK      OK         missing   inherit missing missing OK      OK     
submission_status   missing                missing     OK      missing missing missing     missing    missing missing    missing   missing missing missing missing missing
submissions         missing                missing     OK      OK      OK      OK          OK         OK      OK         OK        inherit OK      OK      OK      OK     
submit_clar         missing                missing     inherit OK      missing stub        stub       missing missing    OK        inherit OK      missing OK      OK     
submit_solution     missing                missing     inherit OK      OK      OK          OK         OK      OK         OK        inherit OK      missing OK      OK     
tasks               OK                     missing     OK      OK      OK      OK          OK         OK      OK         OK        inherit OK      OK      OK      OK     
```
