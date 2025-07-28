import unittest

from flask import json

from reformers_model_api_server.models.application_problem_json import ApplicationProblemJson  # noqa: E501
from reformers_model_api_server.models.info_create_model import InfoCreateModel  # noqa: E501
from reformers_model_api_server.test import BaseTestCase


class TestModelGeneratorsController(BaseTestCase):
    """ModelGeneratorsController integration test stubs"""

    def test_info_model_generator(self):
        """Test case for info_model_generator

        Get information about model generator
        """
        headers = { 
            'Accept': 'application/json',
            'Authorization': 'Bearer special-key',
        }
        response = self.client.open(
            '/model-generators/{generator_name}/{generator_tag}'.format(generator_name='generator_name_example', generator_tag='generator_tag_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_list_model_generators(self):
        """Test case for list_model_generators

        Get list of model generator names
        """
        headers = { 
            'Accept': 'application/json',
            'Authorization': 'Bearer special-key',
        }
        response = self.client.open(
            '/model-generators',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
