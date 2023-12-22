from utilities.testing import ViewTestCases

from netbox_powerdns_sync.tests.custom import ModelViewTestCase
from netbox_powerdns_sync.models import ApiServer


class ApiServerTestCase(
    ModelViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):

    model = ApiServer

    form_data = {
        'name': 'server4',
        'api_url': 'http://localhost:1111/api/v1',
        'api_token': '1111',
        'description': 'server4 description',
        'enabled': True,
    }

    @classmethod
    def setUpTestData(cls):
        server1 = ApiServer.objects.create(
            name='server1',
            api_url='http://server1.example.com:1111/api/v1',
            api_token= '1111',
        )
        server2 = ApiServer.objects.create(
            name='server2',
            api_url='http://server2.example.com:1111/api/v1',
            api_token= '1111',
        )
        server3 = ApiServer.objects.create(
            name='server3',
            api_url='http://server3.example.com:1111/api/v1',
            api_token= '1111',
        )
        cls.csv_update_data = (
            'id,description',
            f'{server1.pk},description 1',
            f'{server2.pk},description 2',
            f'{server3.pk},description 3',
        )
