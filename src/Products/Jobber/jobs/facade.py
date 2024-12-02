##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import inspect

from ..utils.utils import fun_takes_kwargs
from zope.dottedname.resolve import resolve

from ..exceptions import FacadeMethodJobFailed
from .job import Job

_notfound = object()


class FacadeMethodJob(Job):
    """Use this job to execute a method on a facade."""

    name = "Products.Jobber.FacadeMethodJob"
    ignore_result = False

    # Specifying the exceptions a job can raise will avoid the
    # "Unexpected exception" traceback message in zenjobs' log.
    throws = Job.throws + (FacadeMethodJobFailed,)

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job."""
        return "Python API"

    @classmethod
    def getJobDescription(cls, facadefqdn, method, *args, **kwargs):
        """Return a description of the job."""
        facade = facadefqdn.split(".")[-1]
        return "%s.%s %s" % (facade, method, args[0] if args else "")

    @staticmethod
    def getClassPathOf(obj):
        name = obj.__class__.__name__
        module = inspect.getmodule(obj)
        return "%s.%s" % (module.__name__, name)

    def _run(self, facadefqdn, method, *args, **kwargs):
        """Execute a facade's method.

        :param str facadefqdn: classpath to facade class.
        :param str method: name of method on facade class.
        :param *args: positional arguments to method.
        :param **kwargs: keyword arguments to method.
        :return: The return value from the method.
        :raise FacadeMethodJobFailed: method did not succeed.
        """
        facadeclass = resolve(facadefqdn)
        facade = facadeclass(self.dmd)
        bound_method = getattr(facade, method, _notfound)
        if bound_method is _notfound:
            raise FacadeMethodJobFailed(
                "No such attribute on %s: %s" % (facadeclass, method),
            )
        if not callable(bound_method):
            raise FacadeMethodJobFailed(
                "Not a callable method: %s.%s" % (facadeclass, method),
            )

        # Some facade methods were written to accept a 'joblog'
        # parameter provided by this task.
        kwarg_names = set(kwargs)
        kwarg_names.add("joblog")

        # fun_takes_kwargs filters out parameter names not found in the
        # facade method's signature.
        accepted = fun_takes_kwargs(bound_method, kwarg_names)

        # If 'joblog' was not filtered out, add it to kwargs.
        if "joblog" in accepted:
            kwargs["joblog"] = self.log

        # Rebuild kwargs to include only accepted parameter names.
        kwargs = {k: v for k, v in kwargs.iteritems() if k in accepted}
        result = bound_method(*args, **kwargs)

        # Expect result = {'success': boolean, 'message': string}
        # Some old facade method jobs return None.
        if result:
            try:
                if not result["success"]:
                    raise FacadeMethodJobFailed(str(result))
                return result["message"]
            except (TypeError, KeyError):
                self.log.warn(
                    "The output from job %s is not in the right format: "
                    "%s.%s returned %s",
                    self.request.id,
                    facadefqdn,
                    bound_method,
                    result,
                )
                return result


from Products.Jobber.zenjobs import app
app.register_task(FacadeMethodJob)
