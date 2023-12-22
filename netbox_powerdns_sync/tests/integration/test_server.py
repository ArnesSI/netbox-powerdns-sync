from utilities.testing import TestCase
import powerdns
from ...models import ApiServer


class ServerTestCase(TestCase):
    def setUp(self):
        self.server = ApiServer.objects.create(name='local', api_url='http://localhost:8081/api/v1', api_token='1234567890a')
        return super().setUp()
    
    def test_api_server(self):
        api = self.server.api
        self.assertEqual(api.sid, 'localhost')
