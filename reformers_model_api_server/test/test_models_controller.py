import unittest

from flask import json

from reformers_model_api_server.models.application_problem_json import ApplicationProblemJson  # noqa: E501
from reformers_model_api_server.models.create_model import CreateModel  # noqa: E501
from reformers_model_api_server.models.info_model import InfoModel  # noqa: E501
from reformers_model_api_server.models.list_models import ListModels  # noqa: E501
from reformers_model_api_server.test import BaseTestCase


class TestModelsController(BaseTestCase):
    """ModelsController integration test stubs"""

    def test_create_model(self):
        """Test case for create_model

        Create new model
        """
        create_model = reformers_model_api_server.CreateModel()
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer special-key',
        }
        response = self.client.open(
            '/model-generators/{generator_name}/{generator_tag}/models'.format(generator_tag='generator_tag_example', generator_name='generator_name_example'),
            method='POST',
            headers=headers,
            data=json.dumps(create_model),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_list_models(self):
        """Test case for list_models

        Get information about available models
        """
        headers = { 
            'Accept': 'application/json',
            'Authorization': 'Bearer special-key',
        }
        response = self.client.open(
            '/model-generators/{generator_name}/{generator_tag}/models'.format(generator_name='generator_name_example', generator_tag='generator_tag_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
