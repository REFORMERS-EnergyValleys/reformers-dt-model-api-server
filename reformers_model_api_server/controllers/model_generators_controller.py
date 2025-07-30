# import connexion
from connexion.problem import problem
from flask import current_app
from functools import partial
from typing import Any, Union

from reformers_model_api_server.models.info_model_generator import InfoModelGenerator  # noqa: E501
from reformers_model_api_server.controllers.util import convert_to_nested_dict, paginated_search  # noqa: E501

from reformers_model_repo_client import RetrieveBlobsApi, RetrieveManifestsApi, SearchRepositoryApi
from reformers_model_repo_client.exceptions import NotFoundException

def info_model_generator(
        generator_name: str,
        generator_tag: str
    ) -> Union[InfoModelGenerator, problem]:
    """
    Get information about model generator

    :param generator_name:
    :type generator_name: str
    :param generator_tag:
    :type generator_tag: str
    :rtype: Union[InfoModelGenerator, problem]
    """
    with current_app.app_context():

        manifest_api_instance = RetrieveManifestsApi(current_app.repo_client)

        try:
            # Retrieve manifest of model generator image from the repository.
            manifest = manifest_api_instance.get_manifest_generator(generator_name, generator_tag)
        except NotFoundException as e:
            return problem(
                title='Not Found',
                detail='Model generator not found',
                status=404,
                type='about:blank',
            )
        except Exception as e:
            raise Exception(f'Exception when calling RetrieveManifestsApi->get_manifest_generator: {e}\n')

        blobs_api_instance = RetrieveBlobsApi(current_app.repo_client)

        try:
            # Retrieve blob of model generator image from the repository.
            blob = blobs_api_instance.get_blob_generator(generator_name, manifest.config.digest)
        except Exception as e:
            raise Exception(f'Exception when calling RetrieveBlobsApi->get_blob_generator: {e}\n')

        if not blob.config.labels:
            return problem(
                title='Internal Server Error',
                detail='Model generator info invalid (labels missing)',
                status=500,
                type='about:blank',
            )

        # Get configuration labels from blob.
        config_labels = convert_to_nested_dict(blob.config.labels)
        if not ((generator_name in config_labels) and (generator_tag in config_labels[generator_name])):
            return problem(
                title='Internal Server Error',
                detail='Model generator info invalid (labels missing)',
                status=500,
                type='about:blank',
            )

        # Retrieve generator info from labels.
        generator_info = config_labels[generator_name][generator_tag]
        return InfoModelGenerator(
            generator_name=generator_name,
            generator_tag=generator_tag,
            config=generator_info.get('config', dict()),
            parameters=generator_info.get('parameters', dict()),
            build=generator_info.get('build', dict()),
        )

def list_model_generators() -> dict[str, list[str]] :
    """
    Get list of model generator names

    :rtype: dict[str, list[str]]
    """
    with current_app.app_context():
        # Initialize API search function.
        search_api_instance = SearchRepositoryApi(current_app.repo_client)

        # Initialize search results.
        search_results = dict()

        # Search for available model generators.
        paginated_search(
            search_api_func=partial(
                search_api_instance.search_components,
                repository='model-generators'
            ),
            add_search_item=partial(
                search_add_model_generators_with_tags,
                search_results=search_results
            )
        )

        return search_results

def search_add_model_generators_with_tags(
        search_item: Any,
        search_results: dict
    ) -> None:
    """
    Retrieve relevant information for model generator search item.
    """
    model_generator_name = search_item.name
    model_generator_tags = search_results.get(model_generator_name, None)
    if model_generator_tags:
        model_generator_tags.append(search_item.version)
    else:
        search_results[search_item.name] = [search_item.version]
