from hashlib import sha1

from zope.interface import implementer

from Products.ZenHub.interfaces import ICollectorEventFingerprintGenerator


@implementer(ICollectorEventFingerprintGenerator)
class DefaultFingerprintGenerator(object):
    """Generates a fingerprint using a checksum of properties of the event."""

    weight = 100

    _IGNORE_FIELDS = ("rcvtime", "firstTime", "lastTime")

    def generate(self, event):
        fields = []
        for k, v in sorted(event.iteritems()):
            if k not in DefaultFingerprintGenerator._IGNORE_FIELDS:
                if isinstance(v, unicode):
                    v = v.encode("utf-8")
                else:
                    v = str(v)
                fields.extend((k, v))
        return sha1("|".join(fields)).hexdigest()
