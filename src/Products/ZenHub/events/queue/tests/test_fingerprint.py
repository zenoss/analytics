from unittest import TestCase

from zope.interface.verify import verifyObject

from ..fingerprint import (
    DefaultFingerprintGenerator,
    ICollectorEventFingerprintGenerator,
    sha1,
)


class DefaultFingerprintGeneratorTest(TestCase):
    def test_init(t):
        fingerprint_generator = DefaultFingerprintGenerator()

        # the class Implements the Interface
        t.assertTrue(
            ICollectorEventFingerprintGenerator.implementedBy(
                DefaultFingerprintGenerator
            )
        )
        # the object provides the interface
        t.assertTrue(
            ICollectorEventFingerprintGenerator.providedBy(
                fingerprint_generator
            )
        )
        # Verify the object implments the interface properly
        verifyObject(
            ICollectorEventFingerprintGenerator, fingerprint_generator
        )

    def test_generate(t):
        """Takes an event, chews it up and spits out a sha1 hash
        without an intermediate function that returns its internal fields list
        we have to duplicate the entire function in test.
        REFACTOR: split this up so we can test the fields list generator
        and sha generator seperately.
        Any method of generating the a hash from the dict should work so long
        as its the same hash for the event with the _IGNORE_FILEDS stripped off
        """
        event = {"k%s" % i: "v%s" % i for i in range(3)}
        fields = []
        for k, v in sorted(event.iteritems()):
            fields.extend((k, v))
        expected = sha1("|".join(fields)).hexdigest()

        # any keys listed in _IGNORE_FIELDS are not hashed
        for key in DefaultFingerprintGenerator._IGNORE_FIELDS:
            event[key] = "IGNORE ME!"

        fingerprint_generator = DefaultFingerprintGenerator()
        out = fingerprint_generator.generate(event)

        t.assertEqual(out, expected)
