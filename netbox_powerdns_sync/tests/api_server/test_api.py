from utilities.testing import APIViewTestCases
from ..custom import APITestCase
from ...models import ApiServer


class ApiServerTest(
        APITestCase, 
        APIViewTestCases.GetObjectViewTestCase,
        APIViewTestCases.ListObjectsViewTestCase,
        APIViewTestCases.CreateObjectViewTestCase,
        APIViewTestCases.UpdateObjectViewTestCase,
        APIViewTestCases.DeleteObjectViewTestCase):
    model = ApiServer
    brief_fields = ['api_token', 'api_url', 'display', 'enabled', 'id', 'name', 'url']
    create_data = [
        {
            'name': 'server4',
            'api_url': 'http://server4.local:2222/api/v1',
            'api_token': '2222',
            'enabled': False,
        },
        {
            'name': 'server5',
            'api_url': 'http://server5.local:2222/api/v1',
            'api_token': '2222',
            'enabled': False,
        },
        {
            'name': 'server6',
            'api_url': 'http://server6.local:2222/api/v1',
            'api_token': '2222',
            'enabled': False,
        },
    ]
    bulk_update_data = {
        'description': 'new description',
    }

    @classmethod
    def setUpTestData(cls) -> None:
        ApiServer.objects.create(name='server1', api_url='https://server1.example.com/api/v1', api_token='1111', enabled=True)
        ApiServer.objects.create(name='server2', api_url='https://server2.example.com/api/v1', api_token='1111', enabled=True)
        ApiServer.objects.create(name='server3', api_url='https://server3.example.com/api/v1', api_token='1111', enabled=True)
