import os
import unittest

from vlamb import Vtapi, VtapiError


class TestVtapi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not all(key in os.environ for key in ['VTIGER_HOST', 'VTIGER_USER', 'VTIGER_PASS']):
            cls.skipTest("environment variables not configured")

    def test_login(self):
        with Vtapi(os.environ['VTIGER_HOST']) as api:
            api.login(os.environ['VTIGER_USER'], os.environ['VTIGER_PASS'])

    def test_login_fail(self):
        with Vtapi(os.environ['VTIGER_HOST']) as api, self.assertRaises(VtapiError) as fail:
            api.login(os.environ['VTIGER_USER'], 'bogus')
        self.assertEqual("INVALID_USER_CREDENTIALS: Invalid username or password", str(fail.exception))

    def test_count(self):
        with Vtapi(os.environ['VTIGER_HOST']) as api:
            api.login(os.environ['VTIGER_USER'], os.environ['VTIGER_PASS'])
            self.assertGreater(api.count('Quotes'), 0)

    def test_retrieve(self):
        with Vtapi(os.environ['VTIGER_HOST']) as api:
            api.login(os.environ['VTIGER_USER'], os.environ['VTIGER_PASS'])
            self.assertIn('website', api.retrieve('CompanyDetails')[0])
