import ast
import os
from functools import wraps

__all__ = ("MIBLoader",)


def coroutine(func):
    """Decorator for initializing a generator as a coroutine.
    """
    @wraps(func)
    def start(*args, **kw):
        coro = func(*args, **kw)
        coro.next()
        return coro
    return start


@coroutine
def broadcast(targets):
    """Send inputs to all targets.
    """
    if not isinstance(targets, (list, tuple)):
        targets = [targets]
    while True:
        item = (yield)
        for target in targets:
            target.send(item)


@coroutine
def transform(expr, target):
    """Use the expr to convert the input and send the result to the target.
    """
    while True:
        item = (yield)
        if not isinstance(item, (list, tuple)):
            item = [item]
        item = expr(*item)
        target.send(item)


@coroutine
def iterate(factory, target):
    """Uses the factory to create an iterable, then iterates over the
    iterable, sending each produced item to the target.
    """
    while True:
        source = (yield)
        iterable = factory(source)
        for item in iterable:
            target.send(item)


@coroutine
def file_writer(path):
    """Accepts a tuple of a filename and a string containing the contents
    of the file.  The content is saved to a file named by filename.
    """
    while True:
        filename, contents = (yield)
        pathname = os.path.join(path, filename)
        with open(pathname, 'w') as fd:
            fd.write(contents)
            fd.flush()


@coroutine
def eval_python_literal(target):
    """Accepts a string containing a Python literal expression and compiles
    it into the corresponding object.  The result is forwarded to the target.
    """
    while True:
        definition = (yield)
        mib = ast.literal_eval(definition)
        target.send(mib)


@coroutine
def add_mib(manager, organizer):
    """Accepts Python dict that represents the data for a MIB module and
    adds it to the DMD.
    """
    while True:
        mib = (yield)
        manager.add(mib, organizer)


class MIBLoader(object):
    """Load the output from smidump into the DMD.

    Optionally saves the output to files.
    """

    def __init__(self, manager, organizer, savepath=None):
        """
        """
        self._mgr = manager

        # Build the loader pipeline.  It's as if it were separate
        # Unix commands piped together, i.e.
        #
        # $ cat dump | split_into_defs \
        #            | eval_python_literal \
        #            | add_mib organizer
        #
        loader = iterate(
            lambda dump: dump.definitions,
            eval_python_literal(
                add_mib(manager, organizer)
            )
        )

        if savepath:
            # A save path is specified so prefix a save pipeline to the
            # load pipeline.  There isn't a Unix pipe equivalent because
            # 'broadcast' creates multiple pipelines which isn't possible
            # on the command line.
            loader = broadcast([
                iterate(
                    lambda dump: dump.files,
                    # Add a '.py' suffix to the filename
                    transform(
                        lambda x, y: (x + ".py", y),
                        file_writer(savepath)
                    )
                ),
                # Re-use the loader defined above
                loader
            ])
        self._pipeline = loader

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._pipeline.close()

    def load(self, dump):
        self._pipeline.send(dump)

    def close(self):
        self._pipeline.close()
