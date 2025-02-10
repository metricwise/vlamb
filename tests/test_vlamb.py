import os
import unittest

from vlamb import login, Vtapi, VtapiError


class TestVtapi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not all(key in os.environ for key in ['VTIGER_HOST', 'VTIGER_USER', 'VTIGER_PASS']):
            cls.skipTest("environment variables not configured")

    def test_count(self):
        with login() as api:
            self.assertGreater(api.count('Quotes'), 0)

    def test_login_fail(self):
        with Vtapi(os.environ['VTIGER_HOST']) as api, self.assertRaises(VtapiError) as fail:
            api.login(os.environ['VTIGER_USER'], 'bogus')
        self.assertEqual("INVALID_USER_CREDENTIALS: Invalid username or password", str(fail.exception))

    def test_retrieve(self):
        with login() as api:
            self.assertIn('website', api.retrieve('CompanyDetails')[0])
