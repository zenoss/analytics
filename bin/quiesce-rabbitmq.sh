#!/usr/bin/env bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

# http://www.rabbitmq.com/memory.html

function help()
{
    cat <<CAT_EOF >&2
Usage: $0 { status | pause | resume | help }

    PAUSE_CHECK_TIMEOUT env var may be overridden from default of 60 seconds
        amount of time to look for locked=true after calling pause

CAT_EOF
}


function datetimestamp()
{
    TZ=UTC date +"%Y-%m-%dT%Hh%Mm%SsZ"
}


function die
{
    echo "$(datetimestamp): ERROR: ${*}" >&2
    exit 1
}


function logInfo
{
    echo "$(datetimestamp): INFO: ${*}" >&2
}


function getConfValue
{
    local conf="$1"     # configuration file to use (full path)
    local key="$2"      # config value to check for
    local prepend="$3"  # optional: prepend this to value if value is set
    value=$(awk -v key="$key" '$1 == key {print $2; exit(0);}' "$conf")
    if [[ -n $prepend ]]; then
        if [[ -n $value ]]; then
            echo "$prepend'$value'"
        fi
    else
        echo $value
    fi
}


function getLogFile()
{
    echo "$VARDIR/$(basename $0).txt"
}


function get_rabbitmq_setting()
{
    local key="$1"

    # [root@localhost ~]# rabbitmqctl status |grep vm_memory_high_watermark
    # {vm_memory_high_watermark,0.4},

    (
        set -o pipefail
        rabbitmqctl status | egrep -o "{$key,.+}" | cut -f2 -d',' | cut -f1 -d'}'
    )
}


function do_status()
{
    local vm_memory_high_watermark=$(get_rabbitmq_setting vm_memory_high_watermark)
    case "$vm_memory_high_watermark" in
        "0.0")
            echo "IS_PAUSED: vm_memory_high_watermark: $vm_memory_high_watermark"
        ;;

        [0-9.]*)
            echo "IS_NOT_PAUSED: vm_memory_high_watermark: $vm_memory_high_watermark"
        ;;

        *)
            die "unable to determine rabbitmqctl status for vm_memory_high_watermark"
        ;;
    esac
}


function do_pause()
{
    local timeout="$1"

    local vm_memory_high_watermark=$(get_rabbitmq_setting vm_memory_high_watermark)
    case "$vm_memory_high_watermark" in
        "0.0")
            logInfo "rabbitmq is already paused - vm_memory_high_watermark already set"
            return 0
        ;;

        [0-9.]*)
            # [root@localhost ~]# rabbitmqctl set_vm_memory_high_watermark 0
            # Setting memory threshold on rabbit@localhost to 0.0 ...
            # ...done.

            local logfile=$(getLogFile $dbname)
            {
                echo "# $(datetimestamp): value of vm_memory_high_watermark"
                echo "vm_memory_high_watermark $vm_memory_high_watermark"
            } >"$logfile"

            rabbitmqctl set_vm_memory_high_watermark 0
            sleep 2
            for numtries in $(eval echo {1..$timeout}); do
                logInfo "Checking lock status (try: $numtries/$timeout):"
                local output=$($0 status 2>&1)
                echo "$output" >&2
                if [[ $output =~ "IS_NOT_PAUSED:" ]]; then
                    sleep 1
                elif [[ $output =~ "IS_PAUSED:" ]]; then
                    return 0
                else
                    sleep 1
                fi
            done
            return 1
        ;;

        *)
            die "unable to retrieve rabbitmq vm_memory_high_watermark"
        ;;
    esac

    return 1
}


function do_resume()
{
    local logfile=$(getLogFile $dbname)
    if [[ ! -f $logfile ]]; then
        logInfo "rabbitmq was not previously paused - no action taken to resume"
        return 0
    fi

    local vm_memory_high_watermark=$(getConfValue "$logfile" vm_memory_high_watermark)

    case "$vm_memory_high_watermark " in
        "0.0")
            vm_memory_high_watermark="0.4"  # incorrect setting, reset to rabbitmq default of 0.4
        ;;

        [^0-9.]*)
            # do nothing - use value from logfile
        ;;

        *)
            vm_memory_high_watermark="0.4"  # incorrect setting, reset to rabbitmq default of 0.4
        ;;
    esac

    # [root@localhost ~]# rabbitmqctl set_vm_memory_high_watermark 0.4
    # Setting memory threshold on rabbit@localhost to 0.4 ...
    # ...done.

    rabbitmqctl set_vm_memory_high_watermark $vm_memory_high_watermark
}


function main()
{
    [[ $(whoami) == root ]] || die "required user ($(whoami)) is not root"
    VARDIR="/etc/rabbitmq"
    [[ -n "$VARDIR" ]] || die "VARDIR env var is not set"
    [[ -d "$VARDIR" ]] || die "VARDIR=$VARDIR is not a directory"
    export RABBITMQ_NODENAME="$(source /etc/rabbitmq/rabbitmq-env.conf; echo $NODENAME)"

    CMD="$1"
    shift
    case "$CMD" in
        status)
            do_status
	    ;;

        pause)
            local timeout=${PAUSE_CHECK_TIMEOUT:-60}
            do_pause "$timeout"
	    ;;

        resume)
            do_resume
	    ;;

        help)
	        help
	    ;;

        *)
	        help
	        exit 1
    esac
}


if [[ "$(basename $0)" == "quiesce-rabbitmq.sh" ]]; then
    main "$@"
    exit $?
fi

