##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from .utils import coroutine, into_tuple

log = logging.getLogger("zen.configcache.modelchange.pipeline")


class Pipe(object):
    """
    Abstract base class for the pipes in a pipeline.

    A pipeline is a sequence of generators (coroutines) where each generator
    returns data that is forward to the next generator.  The `node` method
    creates the generator.

    Pipelines are push-style, meaning that the generators do not run until
    data is sent into the pipeline. Calling `send` on the generator returned
    by `node` pushes data into the pipeline.  The `send` function blocks until
    the pipeline has finished.

    A Pipe may have one or more outputs or no outputs.  Each output includes
    an ID to identify which Pipe the output is forwarded to.  If there's only
    one output, no ID is required and the default ID is used.

    Use the `connect` method to connect one Pipe to another.

    Returning None from `run` (an Action object) stops the pipeline.  When
    stopped in this way, the pipeline is ready for the next input.

    :param targets: References to the next nodes in the pipeline.
    :type targets: Dict[Any, GeneratorType]
    :param run: References the callable that's invoked when data is applied.
    :type run: Action
    """

    def __init__(self, action):
        """Initialize a Pipe instance.

        :param action: Called to process the data passed to this node.
        :type action: callable
        """
        self.targets = {}
        self.run = action

    @coroutine
    def node(self):
        """Returns the node that forms the pipeline."""
        while True:
            args = yield
            self.apply(args)

    def apply(self, args):
        """Applies the arguments to the action."""
        args = into_tuple(args)
        results = self.run(*args)
        if results is None:
            return
        results = into_tuple(results)
        if len(results) == 1:
            tid, output = self.run.DEFAULT, results[0]
        else:
            tid, output = results[0], results[1]
        if tid not in self.targets:
            log.warn("no such target ID: %s", tid)
            return
        self.targets[tid].send(output)

    def connect(self, target, tid=None):
        """
        Connects a Pipe to a specific output.

        If this node will have only one output, a default ID can be used.

        :param target: The pipeline node to receive the output.
        :type target: Pipe
        :param tid: The ID of the output.
        :type tid: int
        """
        tid = tid if tid is not None else self.run.DEFAULT
        self.targets[tid] = target.node()


class IterablePipe(Pipe):
    """
    A variation of the Pipe that iterates over the input passing
    each item to `run` rather than passing all the data at once.

    If a `None` is returned by `run`, rather than stopping, an IterablePipe
    continues on to the next item in the iterable.
    """

    def apply(self, args):
        iterable = into_tuple(args)
        for item in iterable:
            super(IterablePipe, self).apply(item)


class Action(object):
    """Base class for action objects passed to Pipes."""

    DEFAULT = object()
    """Default target ID."""

    def __call__(self, *data):
        """
        Processes the given data and returns data that is forwarded to the
        next node in the pipeline.

        If the returned data is intended for a specific target, return a
        two-element tuple where the target ID is the first element and the
        output data is the second element.

        :rtype: Any | (Any, Any)
        """
        raise NotImplementedError("'__call__' method not implemented")
