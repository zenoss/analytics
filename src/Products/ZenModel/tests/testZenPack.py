##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import unittest

from Products.ZenModel.ZenPack import ZenPack


class TestZenPack(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    def test_getZProperties_empty(self):
        class ZenPack1(ZenPack):
            pass

        self.assertEquals(ZenPack1.getZProperties(), {})

    def test_getZProperties_tuple_of_strings(self):
        class ZenPack2(ZenPack):
            packZProperties = [
                ('zMyString', 'default', 'string'),
                ]

        self.assertEquals(ZenPack2.getZProperties(), {
            'zMyString': {
                'type': 'string',
                'defaultValue': 'default',
                },
            })

    def test_getZProperties_data_attr(self):
        class ZenPack3(ZenPack):
            packZProperties_data = {
                'zMyString': {
                    'type': 'string',
                    'defaultValue': 'default',
                    'category': 'My Category',
                    'label': 'My String',
                    'description': 'This is my string.',
                    },
                'zMyNoType': {
                    'defaultValue': 'default',
                    'description': "I don't have a type.",
                    },
                'zMyNoDefault': {
                    'type': 'string',
                    'description': "I don't have a default value.",
                    },
                }

        self.assertEquals(ZenPack3.getZProperties(), {
            'zMyString': {
                'type': 'string',
                'defaultValue': 'default',
                'category': 'My Category',
                'label': 'My String',
                'description': 'This is my string.',
                },
            })

    def test_getZProperties_both_kinds(self):
        class ZenPack4(ZenPack):
            packZProperties = [
                ('zMyString', 'default', 'string'),
                ('zMyLines', ['default'], 'lines'),
                ]

            packZProperties_data = {
                'zMyString': {
                    'type': 'int',
                    'defaultValue': 'new-default',
                    'category': 'Mine',
                    'label': 'My String',
                    'description': 'This is my string.',
                    },
                'zMyBoolean': {
                    'type': 'boolean',
                    'defaultValue': True,
                    'category': 'Mine',
                    'label': 'My Boolean',
                    'description': 'This is my boolean.',
                    },
                }

        self.assertEquals(ZenPack4.getZProperties(), {
            'zMyString': {
                'type': 'string',
                'defaultValue': 'default',
                'category': 'Mine',
                'label': 'My String',
                'description': 'This is my string.',
                },
            'zMyLines': {
                'type': 'lines',
                'defaultValue': ['default'],
                },
            'zMyBoolean': {
                'type': 'boolean',
                'defaultValue': True,
                'category': 'Mine',
                'label': 'My Boolean',
                'description': 'This is my boolean.',
                },
            })
