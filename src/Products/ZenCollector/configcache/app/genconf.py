from __future__ import print_function

import textwrap

from .args import get_subparser

# List of options to not include when generating a config file.
_ARGS_TO_IGNORE = (
    "",
    "configfile",
    "help",
)


class GenerateConfig(object):

    description = "Write an example config file to stdout"

    @staticmethod
    def add_command(subparsers, parsers):
        subp_genconf = get_subparser(
            subparsers, "genconf", GenerateConfig.description
        )
        subp_genconf.set_defaults(
            factory=GenerateConfig,
            parsers=parsers,
        )

    def __init__(self, args):
        self._parsers = args.parsers

    def run(self):
        actions = []
        for parser in self._parsers:
            for action in parser._actions:
                if action.dest in _ARGS_TO_IGNORE:
                    continue
                if any(action.dest == act[1] for act in actions):
                    continue
                actions.append(
                    (
                        action.help,
                        action.dest.replace("_", "-"),
                        action.default,
                    )
                )
        print(_item_as_text(actions[0]))
        for act in actions[1:]:
            print()
            print(_item_as_text(act))


def _item_as_text(item):
    return "{}\n#{} {}".format(
        "\n".join(
            "# {}".format(line) for line in textwrap.wrap(item[0], width=75)
        ),
        item[1],
        item[2],
    )
