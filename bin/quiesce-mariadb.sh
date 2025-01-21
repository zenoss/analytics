#!/usr/bin/env bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


function help()
{
    cat <<CAT_EOF >&2
Usage: $0 { status | pause | resume | help }

    PAUSE_CHECK_TIMEOUT env var may be overridden from default of 60 seconds
        amount of time to look for locked=true after calling pause

    LOCK_HOLD_DURATION env var may be overridden from the default of 600 seconds
        amount of time to hold the database locks
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


function getMysqlConnectionArgs()
{
    local config="$1"
    local dbname="$2"

    local arg
    arg+=" "$(getConfValue "$config" "$dbname-admin-user" "--user=")
    arg+=" "$(getConfValue "$config" "$dbname-admin-password" "--password=")
    arg+=" "$(getConfValue "$config" "$dbname-db" "--database=")
    [[ $arg =~ "--user=" ]] || die "required $dbname-admin-user not found in $config"
    [[ $arg =~ "--database=" ]] || die "required $dbname-db not found in $config"

    echo $arg
}


function getLogFile()
{
    local dbname="$1"
    echo "$VARDIR/$(basename $0)-hold-lock-$dbname.txt"
}


function do_status()
{
    declare dbnames=("$@")

    logInfo "status dbnames:${dbnames[@]}"

    local allLocked=true
    for dbname in "${dbnames[@]}"; do
        local msg_prepend="$(datetimestamp): $$ $(basename $0) hold-lock-$dbname"

        # use pgrep to check for process holding lock
        local result=$(pgrep -fla "mysql.*$(basename $0).*hold-lock-$dbname")
        if [[ -z $result ]]; then
            echo "IS_NOT_LOCKED: $dbname"
            allLocked=false
        else
            # verify process that is holding the lock has done so
            local logfile=$(getLogFile $dbname)
            local search=$(echo "$result"|cut -f2 -d\")
            if grep "$search" "$logfile" >/dev/null; then
                echo "IS_LOCKED: $dbname"
            else
                echo "IS_NOT_LOCKED: $dbname"
                allLocked=false
            fi
        fi
    done

    [[ $allLocked == true ]] && return 0 || return 1   # 0: all are locked
}


function do_hold_lock()
{
    local hold_time="$1"
    local dbname="$2"

    logInfo "hold_lock hold_time:$hold_time dbname:$dbname"

    local args=$(getMysqlConnectionArgs "$GLOBAL_CONF" "$dbname")

    local logfile=$(getLogFile $dbname)
    local msg_prepend="$(datetimestamp): $$ $(basename $0) hold-lock-$dbname"
    echo "$msg_prepend Retrieving read lock for $dbname" >>"$logfile"

    # executing: FLUSH TABLES WITH READ LOCK
    #   http://www.mysqlperformanceblog.com/2012/03/23/how-flush-tables-with-read-lock-works-with-innodb-tables/
    #   http://www.mysqlperformanceblog.com/2006/08/21/using-lvm-for-mysql-backup-and-replication-setup/
    # calling "lock tables for read" to lock all of mysql including
    # zep and zodb, do not use get_lock() which is used exclusively by zodb
    # lock the table; output that it was done; sleep for hold time
    local statements="'FLUSH TABLES WITH READ LOCK \G; SELECT \"$msg_prepend LOCKED\" AS \"\"; SELECT SLEEP($hold_time);'"
    eval exec mysql -A --unbuffered --quick $args -e "$statements" >>"$logfile" 2>&1

    return $?
}


function do_pause()
{
    local timeout="$1"
    shift
    local dbnames=("$@")

    logInfo "pause timeout:$timeout dbnames:${dbnames[@]}"

    for dbname in "${dbnames[@]}"; do
        $0 hold-lock-$dbname &>/dev/null &
        disown
    done
    sleep 2
    for numtries in $(eval echo {1..$timeout}); do
        logInfo "Checking lock status (try: $numtries/$timeout):"
        local output=$($0 status 2>&1)
        echo "$output" >&2
        if [[ $output =~ "IS_NOT_LOCKED:" ]]; then
            sleep 1
        else
            return 0
        fi
    done
    return 1
}


function do_resume()
{
    local dbnames=("$@")

    logInfo "resume dbnames:${dbnames[@]}"

    pkill -f "$(basename $0).*hold-lock"
    sleep 2
    for dbname in "${dbnames[@]}"; do
        local logfile=$(getLogFile $dbname)
        if [[ -f $logfile ]]; then
            mv "$logfile" "$logfile.bak"
        fi
    done
}


function main()
{
    [[ -n "$MARIADB_DB" ]] || die "MARIADB_DB env var is not set"
    [[ -n "$VARDIR" ]] || die "VARDIR env var is not set"
    [[ -d "$VARDIR" ]] || die "VARDIR=$VARDIR is not a directory"
    [[ -n "$CFGDIR" ]] || die "CFGDIR env var is not set"
    [[ -d "$CFGDIR" ]] || die "CFGDIR=$CFGDIR is not a directory"
    export GLOBAL_CONF="$CFGDIR/global.conf"

    dbnames=($MARIADB_DB)

    case "$CMD" in
        status)
            do_status "${dbnames[@]}"
	    ;;

        pause)
            local timeout=${PAUSE_CHECK_TIMEOUT:-60}
            do_pause "$timeout" "${dbnames[@]}"
	    ;;

        resume)
            do_resume "${dbnames[@]}"
	    ;;

        hold-lock-zodb)
            # do not advertise via help that private method 'hold-lock-*' is a valid run command
            local hold_time=${LOCK_HOLD_DURATION:-600}
            do_hold_lock "$hold_time" "zodb"
        ;;

        hold-lock-zep)
            # do not advertise via help that private method 'hold-lock-*' is a valid run command
            local hold_time=${LOCK_HOLD_DURATION:-600}
            do_hold_lock "$hold_time" "zep"
        ;;

        help)
	        help
	    ;;

        *)
	        help
	        exit 1
    esac
}


if [[ "$(basename $0)" == "quiesce-mariadb.sh" ]]; then
    if [[ $(whoami) == "root" ]]; then
        FULLPATH="$(cd $(dirname $0); pwd -P)"
        exec su - zenoss -c "$FULLPATH/$(basename $0) $*"
    fi

    [[ -n "$ZENHOME" ]] || die "ZENHOME env var is not set"

    # Needs these env vars provided from zenfunctions:
    #   VARDIR=$ZENHOME/var
    #   CFGDIR=$ZENHOME/etc
    #source $ZENHOME/bin/zenfunctions

    # START OF HACK for zenfunctions is broken in fedora19 - zenfunctions python wrapper has issues
    export VARDIR=$ZENHOME/var
    export CFGDIR=$ZENHOME/etc
    CMD="$1"
    shift
    # END OF HACK

    main "$@"
    exit $?
fi

