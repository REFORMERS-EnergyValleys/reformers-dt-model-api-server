import unittest

from flask import json

from reformers_model_api_server.models.application_problem_json import ApplicationProblemJson  # noqa: E501
from reformers_model_api_server.models.info_auth import InfoAuth  # noqa: E501
from reformers_model_api_server.test import BaseTestCase


class TestInfoController(BaseTestCase):
    """InfoController integration test stubs"""

    def test_get_auth_info(self):
        """Test case for get_auth_info

        Get authentication info
        """
        headers = { 
            'Accept': 'application/json',
            'Authorization': 'Bearer special-key',
        }
        response = self.client.open(
            '/',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
