import unittest

from flask import json

from reformers_model_api_server.models.application_problem_json import ApplicationProblemJson  # noqa: E501
from reformers_model_api_server.models.info_create_model import InfoCreateModel  # noqa: E501
from reformers_model_api_server.test import BaseTestCase


class TestStatusController(BaseTestCase):
    """StatusController integration test stubs"""

    def test_status_model_creation(self):
        """Test case for status_model_creation

        Retrieve information about model generation tasks
        """
        query_string = [('task-id', 'task_id_example')]
        headers = { 
            'Accept': 'application/json',
            'Authorization': 'Bearer special-key',
        }
        response = self.client.open(
            '/model-generators/{generator_name}/{generator_tag}/status'.format(generator_name='generator_name_example', generator_tag='generator_tag_example'),
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
