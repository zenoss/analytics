#! /usr/bin/env bash   
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__DEFAULT__() {
    # Move service-id argument from beginning to end of argument list.  This
    # allows us to use the next argument as the subcommand.
    serviceid=$1
    shift
    if [[ $# -eq 0 ]]; then
        echo missing zenpack subcommand
        help
        return 1
    fi
    set -- "$@" $serviceid

    if declare -f -- "$1" &> /dev/null; then
        "$@"
    else
        echo unknown zenpack sub-command: \"$1\"
        help
        return 1
    fi
    return $?
}


help() {
    echo "usage:"
    echo "   zenpack-manager install <zenpack_egg_relpath>"
    echo "   zenpack-manager link <zenpack_egg_relpath>"
    echo "   zenpack-manager create <zenpack_name>"
    echo "   zenpack-manager restore"
    echo "   zenpack-manager uninstall <zenpack_name>"
    return 1
}


create() {
    zenpack --create "$@"
    return $?
}

restore() {
    zenpack --restore "$@"
    return $?
}

link() {
    VARPATH_SOURCE=$(unset TERM; echo "from Products.ZenUtils.path import varPath;print varPath('ZenPackSource')" | zendmd --script /dev/stdin)
    if ! [[ -d $VARPATH_SOURCE ]]; then
        echo "Unable to determine install path for linked zenpack, or path does not exist"
        echo "$VARPATH_SOURCE"
        return 1
    fi

    zenpackPath="$1"
    if [[ "${zenpackPath:0:1}" != "/" ]]; then
        # Test for readability of /mnt/pwd
        PWDPATH=/mnt/pwd
        if [[ ! ( -r "$PWDPATH" && -x "$PWDPATH" ) ]] ; then
            echo "Error: The current working directory must be world readable+executable"
            return 1
        fi
        cd "$PWDPATH"
    fi

    # Test for presence of ZenPack file/dir
    if [[ ! -r "$zenpackPath" ]]; then
        echo "Unable to read ZenPack file: '$zenpackPath'"
        echo "The ZenPack must be located in the current working directory and must be specified with a relative path."
        return 1
    fi

    TARGET="$VARPATH_SOURCE"/$(basename "$zenpackPath")
    if [[ -e $TARGET ]]; then
        echo "Location $TARGET already exists, cannot copy zenpack"
        return 1
    fi

    rsync -a "$zenpackPath"/ "$TARGET"/

    shift
    zenpack --link --install "$TARGET" "$@"
    return $?
}

install() {
    zenpackPath=$1
    if [[ "${zenpackPath:0:1}" != "/" ]]; then
        # Test for readability of /mnt/pwd
        PWDPATH=/mnt/pwd
        if [[ ! ( -r "$PWDPATH" && -x "$PWDPATH" ) ]] ; then
            echo "Error: The current working directory must be world readable+executable"
            return 1
        fi
        cd "$PWDPATH"
    fi

    #Test for presence of ZenPack egg
    if [[ ! -r "$zenpackPath" ]]; then
        echo "Unable to read ZenPack file: '$zenpackPath'"
        echo "The ZenPack must be located in the current working directory and must be specified with a relative path."
        return 1
    fi

    zenpack --install "$@"
    return $?
}


uninstall() {
    zenpack --uninstall "$@"
    return $?
}
