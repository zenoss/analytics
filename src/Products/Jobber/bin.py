##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

def main():
    import sys

    import Products.Jobber

    from celery.bin.celery import main
    from Products.ZenUtils.Utils import load_config

    # work-around for celery's `--help` bug.
    _print_help_when_requested()

    # Dynamic configuration shenanigans because Celery can't be re-configured
    # after its initial configuration has been set.
    _configure_celery()

    load_config("signals.zcml", Products.Jobber)

    # All calls to celery need the 'app instance' for zenjobs.
    sys.argv[1:] = ["-A", "Products.Jobber.zenjobs"] + sys.argv[1:]

    sys.exit(main())


# Note: an empty tuple implies repetition of the key
_import_names = {
    "inspect": ("control", "inspect"),
    "list": ("list", "list_"),
    "report": ("celery", "report"),
    "help": ("celery", "help"),
}


def _get_command(modname, cmdname):
    import importlib

    module = importlib.import_module("celery.bin.{}".format(modname))
    return getattr(module, cmdname)


def _print_help_when_requested():
    import sys
    from Products.Jobber.zenjobs import app

    if "--help" not in sys.argv:
        return

    name = sys.argv[1]

    if name == "--help":
        sys.argv[1:] = ["help"]
        return

    if name == "monitor":
        from Products.Jobber.monitor.command import MonitorCommand

        w = MonitorCommand(app=app)
        p = w.create_parser("zenjobs", "monitor")
    else:
        modname, cmdname = _import_names.get(sys.argv[1], (name, name))
        command = _get_command(modname, cmdname)
        cmd = command(app=app)
        p = cmd.create_parser(sys.argv[0], name)

    p.print_help()
    sys.exit(0)


def _configure_celery():
    import argparse
    import sys
    from Products.Jobber import config

    # If '--help' was passed as an argument, don't attempt configuration.
    if "--help" in sys.argv:
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file")

    args, remainder = parser.parse_known_args()
    if not args.config_file:
        return

    cfg = config.getConfig(args.config_file)
    config.ZenCeleryConfig = config.from_config(cfg)
    sys.argv[1:] = remainder
