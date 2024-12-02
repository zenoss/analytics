from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.migrate import UpdateUserDatetimeSettings as uuds


class TestUpdateUserDatetimeSettings(BaseTestCase):

    def test_cutover(self):
        self.testusr_names = {
            'testuser_null': '',
            'testuser_ymd': 'YY/MM/DD',
            'testuser_dmy': 'DD/MM/YY',
            'testuser_mdy': 'MM/DD/YY',
        }

        for uname, df in self.testusr_names.items():
            self.dmd.ZenUsers.manage_addUser(
                uname,
                email='{}@zenoss.com'.format(uname),
                roles=['ZenUser', ]
            )
            self.dmd.ZenUsers.getUserSettings(uname).dateFormat = df

        mig = uuds.UpdateUserDatetimeSettings()
        mig.cutover(self.dmd)

        self.assertEqual(
            self.dmd.ZenUsers.getUserSettings('testuser_ymd').dateFormat,
            'YYYY/MM/DD'
        )
        self.assertEqual(
            self.dmd.ZenUsers.getUserSettings('testuser_dmy').dateFormat,
            'DD/MM/YYYY'
        )
        self.assertEqual(
            self.dmd.ZenUsers.getUserSettings('testuser_mdy').dateFormat,
            'MM/DD/YYYY'
        )
        self.assertEqual(
            self.dmd.ZenUsers.getUserSettings('testuser_null').dateFormat,
            ''
        )
