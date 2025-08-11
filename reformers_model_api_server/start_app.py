import connexion
import docker
import json
import pathlib

from base64 import b64decode
from flask import current_app
from warnings import warn

from reformers_model_api_server import encoder
from reformers_model_repo_client import Configuration, ApiClient, RepositorySettingsApi

def apply_registry_auth_config(
        registry_auth_config_file: str
    ) -> None:
    """
    Retrieve authentication config for accessing the container registries,
    then authenticate docker client to these container registries.

    :param registry_auth_config_file: path to authentication config file
    :type registry_auth_config_file: str
    :rtype: None
    """
    registry_auth_config_file = pathlib.Path(registry_auth_config_file)
    registry_auth_config_file = registry_auth_config_file.resolve(strict=True)

    with open(registry_auth_config_file, 'r') as f:
        config = json.load(f)
        auth_config = config.get('auths', dict())

    docker_client = docker.from_env()

    for registry_url, registry_auth_config in auth_config.items():
        if not registry_auth_config['auth']:
            raise RuntimeError(f'Authentication information for registry missing: {registry_url}')
        registry_auth_info = b64decode(registry_auth_config['auth']).decode('utf-8')

        registry_auth = registry_auth_info.split(':')
        if not 2 == len(registry_auth):
            raise RuntimeError('Invalid repository credentials format')

        try:
            docker_client.login(
                registry=registry_url, username=registry_auth[0], password=registry_auth[1]
            )
        except docker.errors.APIError:
            warn(
                f'Docker login to {registry_url} failed',
                category=RuntimeWarning
            )

    return registry_auth_config

def get_repo_auth(
        host: str,
        repo_auth_config_file: str
    ) -> tuple[str, str]:
    """
    Retrieve authentication config for accessing the repository.

    :param host: host name
    :type host: str
    :param repo_auth_config_file: path to authentication config file
    :type repo_auth_config_file: str
    :return: tuple with username and password
    :rtype: tuple[str, str]
    """
    repo_auth_config_file = pathlib.Path(repo_auth_config_file)
    repo_auth_config_file = repo_auth_config_file.resolve(strict=True)

    with open(repo_auth_config_file, 'r') as f:
        config = json.load(f)
        auth_config = config.get('auths', dict())

    repo_auth_config = auth_config.get(host, dict(auth=None))
    if not repo_auth_config['auth']:
        raise RuntimeError('Authentication information for repository missing')

    repo_auth_info = b64decode(repo_auth_config['auth']).decode('utf-8')
    repo_auth = repo_auth_info.split(':')
    if not 2 == len(repo_auth):
        raise RuntimeError('Invalid repository credentials format')

    return repo_auth

def start_app(
        specification: str,
        host: str,
        repo_auth_config_file: str,
        registry_auth_config_file: str,
        metagenerator_auth_config_file: str,
        remove_containers: bool,
        verify_ssl: bool
    ) -> connexion.App:
    """
    Start the server running the model API app.

    :param specification: OpenAPI specification file name (relative to subfolder 'openapi')
    :param host: URL to repository
    :param registry_auth_config_file: path to authentication config file for accessing the container registries
    :param repo_auth_config_file: path to authentication config file for accessing the repository
    :param remove_containers: set this to false to remove containers after they have exited
    :param verify_ssl: set this to true to verify SSL certificates
    """
    openapi_dir = pathlib.Path(__file__).parent / 'openapi'
    specification_file = openapi_dir / specification
    specification_file = specification_file.resolve(strict=True)

    repo_auth = get_repo_auth(host, repo_auth_config_file)

    repo_config = Configuration(
        host = f'https://{host}',
        username = repo_auth[0],
        password = repo_auth[1]
    )
    repo_config.verify_ssl = verify_ssl

    apply_registry_auth_config(registry_auth_config_file)

    metagenerator_auth_config_file = pathlib.Path(metagenerator_auth_config_file)
    try:
        metagenerator_auth_config_file = metagenerator_auth_config_file.resolve(strict=True)
    except OSError:
        warn(
            f'path {metagenerator_auth_config_file} could not be resoved',
            category=RuntimeWarning
        )

    flask_app = connexion.App(__name__)
    flask_app.app.json_encoder = encoder.JSONEncoder
    flask_app.add_api(specification_file,
                arguments={'title': 'REFORMERS Digital Twin: Model API'},
                pythonic_params=True)

    with flask_app.app.app_context():

        current_app.repo_client = ApiClient(repo_config)
        current_app.metagenerator_auth_config_file = metagenerator_auth_config_file

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
    repo_auth_config = os.environ.get('REPO_AUTH_CONFIG', default='repo-auth-config.json')
    registry_auth_config = os.environ.get('REGISTRY_AUTH_CONFIG', default='registry-auth-config.json')
    metagenerator_auth_config = os.environ.get('METAGENERATOR_AUTH_CONFIG', default='registry-auth-config.json')
    remove = __parse_to_bool(os.environ.get('REMOVE_CONTAINERS', default='True'))
    verify_ssl = __parse_to_bool(os.environ.get('VERIFY_SSL', default='False'))

    return start_app(
        specification, host, repo_auth_config, registry_auth_config, metagenerator_auth_config, remove, verify_ssl
    )
