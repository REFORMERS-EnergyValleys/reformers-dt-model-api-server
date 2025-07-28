import connexion
from typing import Dict
from typing import Tuple
from typing import Union

from reformers_model_api_server.models.application_problem_json import ApplicationProblemJson  # noqa: E501
from reformers_model_api_server.models.info_auth import InfoAuth  # noqa: E501
from reformers_model_api_server import util


def get_auth_info():  # noqa: E501
    """Get authentication info

     # noqa: E501


    :rtype: Union[InfoAuth, Tuple[InfoAuth, int], Tuple[InfoAuth, int, Dict[str, str]]
    """
    auth_time = connexion.context['token_info'].get('auth_time')
    return InfoAuth(auth_time)
