import connexion
import json
import pathlib

from base64 import b64decode
from flask import current_app

from reformers_model_api_server import encoder
from reformers_model_repo_client import Configuration, ApiClient, RepositorySettingsApi


def start_app(specification, host, auth_config, remove_containers, verify_ssl):

    openapi_dir = pathlib.Path(__file__).parent / 'openapi'
    specification_file = openapi_dir / specification
    specification_file = specification_file.resolve(strict=True)

    auth_config_file = pathlib.Path(auth_config)
    auth_config_file = auth_config_file.resolve(strict=True)

    with open(auth_config_file, 'r') as f:
        config = json.load(f)
        auth_config = config.get('auths', dict())

    repo_auth_config = auth_config.get(host, dict(auth=None))
    if not repo_auth_config['auth']:
        raise RuntimeError('Authentication information for repository missing')

    repo_auth_info = b64decode(repo_auth_config['auth']).decode('utf-8')
    repo_auth = repo_auth_info.split(':')
    if not 2 == len(repo_auth):
        raise RuntimeError('Invalid repository credentials format')

    repo_config = Configuration(
        host = f'https://{host}',
        username = repo_auth[0],
        password = repo_auth[1]
    )
    repo_config.verify_ssl = verify_ssl

    flask_app = connexion.App(__name__)
    flask_app.app.json_encoder = encoder.JSONEncoder
    flask_app.add_api(specification_file,
                arguments={'title': 'REFORMERS Digital Twin: Model API'},
                pythonic_params=True)

    with flask_app.app.app_context():

        current_app.repo_client = ApiClient(repo_config)
        current_app.auth_config_file = auth_config_file

        repo_settings_api = RepositorySettingsApi(current_app.repo_client)
        current_app.repo_settings = {
            rs.name: rs for rs in repo_settings_api.repository_settings()
            }

        current_app.remove_containers = remove_containers

    return flask_app

def start_app_from_env():

    import os

    def __parse_to_bool(s: str):
        return s.upper() not in ['0', 'FALSE']

    specification = os.environ.get('SPECIFICATION', default='openapi.yaml')
    host = os.environ.get('HOST', default='reformers-dev.ait.ac.at')
    auth_config = os.environ.get('AUTH_CONFIG', default='auth-config.json')
    remove = __parse_to_bool(os.environ.get('REMOVE-containers', default='True'))
    verify_ssl = __parse_to_bool(os.environ.get('VERIFY_SSL', default='False'))

    return start_app(specification, host, auth_config, remove, verify_ssl)
