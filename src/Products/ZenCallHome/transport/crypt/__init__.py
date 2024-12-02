##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os
import subprocess

logger = logging.getLogger("zen.callhome")

CRYPTPATH = os.path.dirname(__file__)
GPGCMD = "gpg --batch --no-tty --quiet --no-auto-check-trustdb "


def _getEnv():
    env = os.environ.copy()
    env.pop("GPG_AGENT_INFO", None)
    return env


def encrypt(stringToEncrypt, publicKey):
    cmd = GPGCMD + "--keyring %s --trustdb-name %s -e -r %s" % (
        CRYPTPATH + "/pubring.gpg",
        CRYPTPATH + "/trustdb.gpg",
        publicKey,
    )

    p = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        env=_getEnv(),
        stdout=subprocess.PIPE,
        stderr=open(os.devnull),
    )
    out = p.communicate(input=stringToEncrypt)[0]

    if p.returncode != 0:
        logger.warn("Unable to encrypt payload -- is GPG installed?")
        return None
    return out


def decrypt(stringToDecrypt, symKey):
    cmd = GPGCMD + "--passphrase %s -d" % symKey

    p = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        env=_getEnv(),
        stdout=subprocess.PIPE,
        stderr=open(os.devnull),
    )
    out = p.communicate(input=stringToDecrypt)[0]

    if p.returncode != 0:
        logger.warn("Unable to decrypt payload -- is GPG installed?")
        return None
    return out
