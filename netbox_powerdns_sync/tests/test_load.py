from django.urls import reverse
from django.test import SimpleTestCase

from netbox_powerdns_sync import __version__
from netbox_powerdns_sync.tests.custom import APITestCase


class NetboxDnsVersionTestCase(SimpleTestCase):
    """
    Test for netbox_inventory package
    """

    def test_version(self):
        assert __version__ == "0.0.8"


class AppTest(APITestCase):
    """
    Test the availability of the plugin API root
    """

    def test_root(self):
        url = reverse("plugins-api:netbox_powerdns_sync-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)
