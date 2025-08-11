import json
import connexion
import docker
import docker.models.containers

from connexion.problem import problem
from datetime import datetime, timezone
from flask import current_app
from functools import partial
from time import sleep
from typing import Any, Union, Tuple
from urllib.parse import urlparse

from reformers_model_api_server.models.info_create_model import InfoCreateModel  # noqa: E501
from reformers_model_api_server.models.info_model import InfoModel  # noqa: E501
from reformers_model_api_server.models.info_model_generator import InfoModelGenerator  # noqa: E501
from reformers_model_api_server.models.list_models import ListModels  # noqa: E501
from reformers_model_api_server.models.request_create_model import RequestCreateModel  # noqa: E501
from reformers_model_api_server.controllers.model_generators_controller import info_model_generator, list_model_generators
from reformers_model_api_server.controllers.util import get_model_artifact_asset_type, paginated_search, create_task_id, container_name, get_model_image_labels, get_from_nested_dict

from reformers_model_repo_client import HandleArtifactsApi, SearchRepositoryApi

def create_model(
        generator_name: str,
        generator_tag: str,
        request_create_model: Union[dict, bytes]
    ) -> Union[Tuple[InfoModel, int], problem]:
    """
    Create new model

    :param generator_name:
    :type generator_name: str
    :param generator_tag:
    :type generator_tag: str
    :param request_create_model:
    :type request_create_model: dict | bytes
    :rtype: Union[Tuple[InfoModel, int], problem]
    """
    if not connexion.request.is_json:
        return problem(
            title="Interal Server Error",
            detail="Creation of new model failed: request body is not JSON data",
            status=500,
        )

    try:
        info_create_model = RequestCreateModel.from_dict(request_create_model)

        # Get info on model generator.
        info_generator = info_model_generator(generator_name, generator_tag)

        if not type(info_generator) == InfoModelGenerator:
            return info_generator

        if info_create_model.parameters:
            for p in info_create_model.parameters.keys():
                if not (p in info_generator.config or p in info_generator.parameters):
                    return problem(
                        title='Bad Request',
                        detail=f'Invalid model generator parameters: unknown parameter ({p})',
                        status=400,
                        )

        with current_app.app_context():

            model_name = info_create_model.model_name
            model_tag = info_create_model.model_tag
            creation_date = datetime.now(timezone.utc)

            env = info_create_model.parameters.copy() if info_create_model.parameters else dict()
            env['MODEL_NAME'] = model_name
            env['MODEL_TAG'] = model_tag
            env['CREATED'] = creation_date.isoformat()
            env['EXTRA_FLAGS'] = '--cache=true'
            if not current_app.repo_client.configuration.verify_ssl:
                env['EXTRA_FLAGS'] = '--skip-tls-verify ' + (env.get('EXTRA_FLAGS', str()))

            registry_info = current_app.repo_settings['model-generators']
            registry_format = registry_info.format
            if 'docker' != registry_format:
                return problem(
                    title='Interal Server Error',
                    detail='Creation of new model failed: generator container registry not configured',
                    status=500,
                    )
            registry_port = registry_info.additional_properties[registry_format]['httpPort']
            registry_host = urlparse(current_app.repo_client.configuration.host).hostname
            registry_prefix = f'{registry_host}:{registry_port}'

            docker_client = docker.from_env()

            container : docker.models.containers.Container = docker_client.containers.run(
                name=container_name(model_name, model_tag, creation_date),
                image=f'{registry_prefix}/{generator_name}:{generator_tag}',
                volumes=[f'{current_app.metagenerator_auth_config_file}:/workspace/config.json:ro'],
                environment=env,
                detach=True,
                remove=current_app.remove_containers,
                )

            timeout = 20
            sleep_time = 1
            elapsed_time = 0
            while container.status != 'running':
                if container.status == 'exited':
                    if current_app.remove_containers:
                        raise RuntimeError('failed to start the generator')
                    else:
                        logs = container.logs().decode('utf-8')
                        raise RuntimeError(f'failed to start the generator: {logs}')
                if elapsed_time >= timeout:
                    raise RuntimeError('timeout')

                sleep(sleep_time)
                elapsed_time += sleep_time

                container.reload() # Load this object from the server again and update attrs with the new data.

            return (
                InfoCreateModel(
                    task_id=create_task_id(model_name, model_tag, creation_date),
                    creation_date=creation_date,
                    status='pending'
                ),
                202 # Request has been accepted for processing.
            )

    except Exception as ex:

        return problem(
            title='Interal Server Error',
            detail=f'Creation of new model failed: {ex}',
            status=500,
        )


def list_models(
          generator_name: str,
          generator_tag: str
    ) -> Union[ListModels, problem]:
    """
    Get information about available models

    :param generator_name:
    :type generator_name: str
    :param generator_tag:
    :type generator_tag: str
    :rtype: Union[ListModels, Tuple[ListModels, int], Tuple[ListModels, int, Dict[str, str]]]
    """
    # Get list of available generators.
    available_model_generators = list_model_generators()

    # Check generator name.
    if generator_name not in available_model_generators:
        return problem(
            title='Not Found',
            detail='Model generator not found',
            status=404,
            type='about:blank',
        )

    # Check generator tag.
    if generator_tag not in available_model_generators[generator_name]:
        return problem(
            title='Not Found',
            detail='Model generator not found (unknown version)',
            status=404,
            type='about:blank',
        )

    with current_app.app_context():
        # Initialize API search function.
        search_api_instance = SearchRepositoryApi(current_app.repo_client)

        # Initialize search results.
        search_results = dict()

        # Start with search for model images, ...
        search_model_images_format = 'docker'
        paginated_search(
            search_api_func=partial(
                search_api_instance.search_components,
                name=f'*{generator_name}?{generator_tag}*',
                format=search_model_images_format,
            ),
            add_search_item=partial(
                search_add_model_images_with_tags,
                search_results=search_results,
                format=search_model_images_format
            )
        )

        # ... then continue with search for model artifacts.
        search_model_artifacts_format = 'maven2'
        paginated_search(
            search_api_func=partial(
                search_api_instance.search_components,
                group=f'*{generator_name}?{generator_tag}*',
                format=search_model_artifacts_format,
            ),
            add_search_item=partial(
                search_add_model_artifacts_with_tags,
                search_results=search_results,
                format=search_model_artifacts_format
            )
        )

        return ListModels(
            generator_name=generator_name,
            generator_tag=generator_tag,
            models=search_results
            )

def search_add_model_images_with_tags(
        search_item: Any,
        search_results: dict,
        format: str,
    ) -> None:
    """
    Retrieve relevant information for model image search item.
    """
    model_image_name = search_item.name
    model_version = search_item.version

    model_image_name_parts = model_image_name.split('/')
    if model_image_name_parts[-1] == 'cache':
        return # This is an artifact of the build cache, skip this search result.
    else:
        generator_name, generator_tag, model_name = model_image_name.split('/')

    with current_app.app_context():
        # Retrieve model image config.
        image_labels = get_model_image_labels(
            generator_name, generator_tag, model_name, model_version, current_app.repo_client
        )

    print('IMAGE_LABELS:', image_labels)

    # Retrieve generation parameters from config labels.
    generation_parameters = get_from_nested_dict(
        image_labels, [generator_name, generator_tag, model_name, model_version]
    )

    # Retrieve meta-information about (optional) runtime arguments for this specific model.
    model_parameters = generation_parameters.pop('parameters', {'optional': {}})
    model_optional_parameters = model_parameters.pop('optional', {})

    # Retrieve (meta-)information about this specific model.
    model_info = generation_parameters.pop('info', None)

    image_info = InfoModel(
        parameters=model_parameters,
        optional_parameters=model_optional_parameters,
        info=model_info,
        generation_parameters=generation_parameters,
        image_name=model_image_name,
        image_tag=model_version,
        format=format
    )

    all_model_versions = search_results.setdefault(model_name, dict())
    all_model_versions[model_version] = image_info

def search_add_model_artifacts_with_tags(
        search_item: Any,
        search_results: dict,
        format: str
    ) -> None:
    """
    Retrieve relevant information for model artifact search item.
    """
    model_name = search_item.name
    model_version = search_item.version

    generator_name, generator_tag = search_item.group.split('.')

    try:
        artifact_type = get_model_artifact_asset_type(search_item)
    except:
        artifact_type = None

    labels_file_name = f'{model_name}-{model_version}-labels'
    labels_file_extension = 'json'

    with current_app.app_context():
        # Retrieve file with labels for model artifact.
        artifacts_api_instance = HandleArtifactsApi(current_app.repo_client)
        try:
            response = artifacts_api_instance.get_artifact_with_http_info(
                generator_name, generator_tag, model_name, model_version,
                labels_file_name, labels_file_extension
            )

            # Check content type is JSON.
            content_type = response.headers['Content-Type']
            if content_type != 'application/json':
                raise RuntimeError(f'unexpected content type for file with labels for model artifact: {content_type}')

            # Parse JSON content from labels file.
            labels_file_content = json.loads(response.data)
        except:
            labels_file_content = None

    # Retrieve generation parameters from config labels.
    generation_parameters = None
    if labels_file_content:
        generation_parameters = labels_file_content.get(generator_name)

    artifact_info = InfoModel(
        generation_parameters=generation_parameters,
        artifact_id=model_name,
        artifact_version=model_version,
        artifact_group_id=search_item.group,
        artifact_type=artifact_type,
        format=format
    )

    all_model_versions = search_results.setdefault(model_name, dict())
    all_model_versions[model_version] = artifact_info
