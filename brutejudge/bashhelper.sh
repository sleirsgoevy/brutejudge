command_not_found_handle ()
{
    { export BJ_PICKLED="$(python3 -m brutejudge.bashhelper "$@" 3>&1 1>&4)"; } 4>&1
}

alias bj=command_not_found_handle
alias hijack="bj hijack"
alias nocheats="bj nocheats"
alias fileio="bj fileio"
