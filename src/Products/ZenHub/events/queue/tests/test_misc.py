from mock import patch
from unittest import TestCase

from ..misc import load_utilities

PATH = {"src": "Products.ZenHub.events.queue.misc"}


class load_utilities_Test(TestCase):
    @patch("{src}.getUtilitiesFor".format(**PATH), autospec=True)
    def test_load_utilities(t, getUtilitiesFor):
        ICollectorEventTransformer = "some transform function"

        def func1():
            pass

        def func2():
            pass

        func1.weight = 100
        func2.weight = 50
        getUtilitiesFor.return_value = (("func1", func1), ("func2", func2))

        ret = load_utilities(ICollectorEventTransformer)

        getUtilitiesFor.assert_called_with(ICollectorEventTransformer)
        # NOTE: lower weight comes first in the sorted list
        # Is this intentional?
        t.assertEqual(ret, [func2, func1])
