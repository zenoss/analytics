import logging
import importlib
import difflib
import json
import mock
import os

from collections import namedtuple, OrderedDict
from itertools import chain, tee

import six

from servicemigration import context, service


log = logging.getLogger("zen.migrate")


def fakeContextFromFile(jsonfile):
    jsonfile = os.path.join(os.path.dirname(__file__), jsonfile)
    return _FakeServiceContext(jsonfile)


class _FakeServiceContext(context.ServiceContext):
    def __init__(self, filename=None):
        self.services = []
        for datum in json.loads(open(filename, "r").read()):
            self.services.append(service.deserialize(datum))
        self.version = self.services[0]._Service__data["Version"]
        # _client is a ref to ZenUtils.controlplane.ControlPlaneClient,
        # which we don't need during unit-tests. So set it to None
        self._client = None
        self.__logFilters = {}
        self.committed = False

    def commit(self, filename=None):
        addedServices = []
        modifiedServices = []
        for svc in self.services:
            if not hasattr(svc, "_Service__data"):
                svc._Service__data = {}
            serial = service.serialize(svc)
            serial["ID"] = serial.get("ID", "new-service")
            serial["Version"] = self.version
            if serial["ID"] == "new-service":
                addedServices.append(serial)
            else:
                modifiedServices.append(serial)

        self.committed = True

    def deployService(self, servicedef, parent):
        if parent._Service__data["ID"] == "new-service":
            raise Exception(
                "Can't deploy a service to a parent that is a new service."
            )
        newservice = service.deserialize(json.loads(servicedef))
        newservice._Service__data["ParentServiceID"] = parent._Service__data[
            "ID"
        ]
        self.services.append(newservice)

    def servicedef(self):
        """
        This method is not available to the real ServiceContext.
        It's only here for testing purposes.
        """
        return sorted(
            [service.serialize(s) for s in self.services],
            key=lambda s: s["Name"],
        )

    def addLogFilter(self, name, value):
        self.__logFilters[name] = {
            "Name": name,
            "Filter": value,
        }

    @property
    def logFilters(self):
        return self.__logFilters


class FakeDmd:
    def getProductName(self):
        return "Resource Manager"


def compare(this, that, path=None):
    """
    Compare two json serialized values.
    Returns an iterable of differences.  Each difference is a pair of
    values.  The first value is the path where difference is found and
    the second value is the difference itself.  The difference may be
    a compare.Diff object or a string having a unified diff format.
    """
    path = path or []
    if isinstance(this, list):
        return _compare_list(this, that, path)
    elif isinstance(this, dict):
        return _compare_dict(this, that, path)
    elif isinstance(this, six.string_types):
        return _compare_string(this, that, path)
    else:
        if this != that:
            return ((path, compare.Diff(this, that)),)
    return ()


def _compare_list(this, that, path):
    if not isinstance(that, list):
        return ((path, compare.Diff(this, that)),)
    if len(this) != len(that):
        return ((path, compare.Diff(this, that)),)
    return (
        (p, d)
        for i, (a, b) in enumerate(zip(this, that))
        for (p, d) in compare(a, b, path + [i])
    )


def _compare_dict(this, that, path):
    if not isinstance(that, dict):
        return ((path, compare.Diff(this, that)),)
    # The json deserialization in serviced does a case-insensitive match
    # on the field name, choosing the last match encountered for any field.
    # The keys are sorted in service-migration, so in the case of
    # duplicates the "most lower-case" is the last and therefore wins.
    # Duplicate this behavior when comparing dictionaries.
    dis = OrderedDict((k.lower(), this[k]) for k in sorted(this))
    dat = OrderedDict((k.lower(), that[k]) for k in sorted(that))

    def get_val(d, k):
        return d.get(k, compare.missingKey)

    keys = sorted(set(chain(dis.iterkeys(), dat.iterkeys())))
    inputs = ((k, (get_val(dis, k), get_val(dat, k))) for k in keys)
    return (
        (p, d) for i, (a, b) in inputs for (p, d) in compare(a, b, path + [i])
    )


def _compare_string(this, that, path):
    if this == that:
        return ()
    if not isinstance(that, six.string_types):
        return ((path, compare.Diff(this, that)),)
    if any("\n" in i for i in (this, that)):
        diff = difflib.unified_diff(
            this.replace("\r", "").split("\n"),
            that.replace("\r", "").split("\n"),
            fromfile="actual",
            tofile="expected",
        )
        # Since we ignored '\r', we need to see if the diff actually
        # found 0 differences, but iterating diff will empty it, so
        # make a copy to count the diffs
        diff, diff2 = tee(diff)
        n_diffs = 0
        for _ in diff2:
            n_diffs += 1
        if n_diffs == 0:
            return ()
        return ((path, diff),)
    else:
        return ((path, compare.Diff(this, that)),)


compare.Diff = namedtuple("Diff", ["actual", "expected"])
compare.missingKey = "<<KEY NOT PRESENT>>"


class ServiceMigrationTestCase(object):
    """
    Superclass of service migration tests.
    Supply the migration module and class, the input servicedef file,
    and the output servicedef file.
    """

    initial_servicedef = ""
    expected_servicedef = ""
    migration_module_name = ""
    migration_class_name = ""
    expected_log_filters = {}

    def setUp(self):
        logging.getLogger().setLevel(logging.CRITICAL)
        self._fakeContext = None

    def tearDown(self):
        self._fakeContext = None
        logging.getLogger().setLevel(logging.NOTSET)

    def _test_cutover(self, svcdef_before, svcdef_after):
        self._fakeContext = fakeContextFromFile(svcdef_before)
        module_name = (
            "Products.ZenModel.migrate.%s" % self.migration_module_name
        )
        sm_context = "%s.sm.ServiceContext" % module_name
        migration = importlib.import_module(module_name)
        if hasattr(self, "dmd"):
            dmd = self.dmd
        else:
            dmd = FakeDmd()
        with mock.patch(sm_context, new=lambda: self._fakeContext):
            with mock.patch.dict(
                "os.environ",
                {
                    "SERVICED_SERVICE_IMAGE": (
                        "67nh3y829fh3dsemstmfjpg11/resmgr_5.0:latest"
                    )
                },
            ):
                getattr(migration, self.migration_class_name)().cutover(dmd)
        actual = self._fakeContext.servicedef()
        expected = fakeContextFromFile(svcdef_after).servicedef()
        failures = 0
        differences = []
        for rpath, rdiff in compare(actual, expected):
            failures += 1
            if isinstance(rdiff, compare.Diff):
                differences.append(
                    (
                        "Difference found: Expected\n"
                        "\n%s\n"
                        "\n  at %s, got\n"
                        "\n%s\n"
                        "\n  instead."
                    )
                    % (rdiff.expected, rpath, rdiff.actual)
                )
            else:
                differences.append(
                    "Difference found: Unified Diff at %s:\n\n%s\n"
                    % (rpath, "\n".join(rdiff))
                )
        if failures:
            self.fail(
                "Migration failed: %s differences found\n\n%s"
                % (failures, "\n\n".join(differences))
            )

    def test_cutover_correctness(self):
        self._test_cutover(self.initial_servicedef, self.expected_servicedef)

        if len(self.expected_log_filters) != len(self._fakeContext.logFilters):
            self.fail(
                "Migration failed: Expected %d log filters; found %d"
                % (
                    len(self.expected_log_filters),
                    len(self._fakeContext.logFilters),
                )
            )

        elif len(self.expected_log_filters) > 0:
            for name, value in self.expected_log_filters.iteritems():
                if name not in self._fakeContext.logFilters:
                    self.fail(
                        "Migration failed: Did not find expected log "
                        "filter '%s'" % name
                    )
                else:
                    actual = self._fakeContext.logFilters[name]["Filter"]
                    if value != actual:
                        self.fail(
                            "Migration failed: for log filter '%s', "
                            "Expected:\n%s\n\nGot:\n%s\n\n"
                            % (name, value, actual)
                        )

        self.assertEqual(self._fakeContext.committed, True)

    def test_cutover_idempotence(self):
        self._test_cutover(self.expected_servicedef, self.expected_servicedef)
