import re
import base64
from datetime import datetime, timezone
from dateutil import parser as datetimeparser

from typing import Any, Callable, Tuple, Optional
from warnings import warn

from reformers_model_repo_client import RepositorySearchResult, RetrieveBlobsApi, RetrieveManifestsApi
from reformers_model_repo_client.models.container_info import ContainerInfo
from reformers_model_repo_client.models.container_info_config import ContainerInfoConfig

def paginated_search(
        search_api_func: Callable,
        add_search_item: Callable[[Any], None]
    ) -> None:
    """
    This helper function generalizes the search through paginated search results.

    :param search_api_func: API function used for searching
    :param add_search_item: function for extracting relevant information from a search item
    """
    # Initialize paginated search.
    continuation_token = None
    next_page = True

    # Iterate through search result pages.
    while next_page:
        # Get search result page.
        search_result_page = search_api_func(
            continuation_token=continuation_token
        )

        # Extract seach result items.
        for search_item in search_result_page.items:
            add_search_item(search_item)

        # Check if there is another search result page.
        continuation_token = search_result_page.continuation_token
        next_page = continuation_token != None

def get_model_artifact_asset_type(
        model_info: RepositorySearchResult
    ) -> str:
    """
    Get type (file extension) of model artifact.
    """
    # Contruct regex pattern for model artifact file.
    asset_name = model_info.name.replace('.', '\.')
    asset_version = model_info.version.replace('.', '\.')
    asset_pattern = re.compile(f'{asset_name}-{asset_version}\.[a-zA-Z0-9.]+')

    # Get all model artifact assets.
    assets = model_info.assets
    # Retrieve asset file names.
    asset_file_names = [a.path.split('/')[-1] for a in assets]
    # Remove asset files with extra classifiers.
    assets_no_classifiers = [a for a in asset_file_names if asset_pattern.fullmatch(a)]
    # Get asset file extensions
    asset_file_extensions = [a.split('.')[-1] for a in assets_no_classifiers]
    # Remove POM and checksum files
    type = [a for a in asset_file_extensions if a not in ['pom', 'md5', 'sha1', 'sha256', 'sha512']]

    if 1 != len(type):
        raise RuntimeError(f'unable to determine asset type: {asset_name}-{asset_version}')

    return type[0]

def get_model_image_blob(
        generator_name: str,
        generator_tag: str,
        model_name: str,
        model_version: str,
        repo_client: Any
    ) -> ContainerInfo:
    # Retrieve manifest of model image from the repository.
    manifest_api_instance = RetrieveManifestsApi(repo_client)
    manifest = manifest_api_instance.get_manifest_model(
        generator_name, generator_tag, model_name, model_version
    )

    # Retrieve blob of model image from the repository.
    blobs_api_instance = RetrieveBlobsApi(repo_client)
    blob = blobs_api_instance.get_blob_model(
        generator_name, generator_tag, model_name, manifest.config.digest
    )

    return blob

def get_model_image_config(
        generator_name: str,
        generator_tag: str,
        model_name: str,
        model_version: str,
        repo_client: Any
    ) -> ContainerInfoConfig:
    blob = get_model_image_blob(
        generator_name, generator_tag, model_name, model_version, repo_client
    )

    if not blob.config:
        raise RuntimeError(
            f'no model image config found for {generator_name}/{generator_tag}/{model_name}:{model_version}'
        )
    else:
        return blob.config

def get_model_image_creation_date(
        generator_name: str,
        generator_tag: str,
        model_name: str,
        model_version: str,
        repo_client: Any
    ) -> Optional[datetime]:
    blob = get_model_image_blob(
        generator_name, generator_tag, model_name, model_version, repo_client
    )

    return datetimeparser.parse(blob.created) if blob.created else None

def get_model_image_labels(
        generator_name: str,
        generator_tag: str,
        model_name: str,
        model_version: str,
        repo_client: Any
    ) -> dict:
    config = get_model_image_config(
        generator_name, generator_tag, model_name, model_version, repo_client
    )

    return convert_to_nested_dict(config.labels) if config.labels else {}

def convert_to_nested_dict(
        data: dict[str, Any],
        conflict_key: str='_value'
    ) -> dict:
    """
    Helper function for converting a dict with dot-separated keys to a nested dict.

    :param data: dict with dot-separated keys
    :param conflict_key: in case dot-separated keys are inconsistent, the items in question will be added with this subkey instead
    :return: nested dict

    # Example

    For instance, the following dict
    ```
    {'a.x': 'AX', 'a.y': 'AY', 'b.x': 'BX', 'b.y': 'BY'}
    ```

    will be converted to
    ```
    {'a': {'x': 'AX','y': 'AY'}, 'b': {'x': 'BX', 'y': 'BY'}}
    ```

    In case the keys are inconsistent, the items in question will be added with subkey `conflict_key` (default='_value') instead.
    For example, in the following dict
    ```
    {'a': 'A', 'a.b': 'AB'}
    ```

    the key 'a' is first associated to a value ('A') and then to a dict ({'b':'B'}).
    The helper function will patch this inconsistency by returning the following dict:
    ```
    {'a': {'_value': 'A', 'b': 'AB'}}
    ```
    """
    # Internal helper function for warnings.
    def warn_conflict(val: Any, key_from: str, key_to:str) -> None:
        warn(
            f'key "{key_from}" is in conflict with a previous key, move previous value "{val}" to key "{key_to}"',
            category=RuntimeWarning
        )

    result = {}
    for k, v in data.items():
        tmp = result

        # Split the dot-separated key to subkeys.
        *keys, final = k.split('.')

        # Iterate through all but the last subkey.
        for subkey in keys:
            # Get item with specified key. If key doesn't exist, insert empty dict.
            tmp2 = tmp.setdefault(subkey.strip(), {})

            # If all keys are consistent, the retrieved item should be a dict.
            # Apply a patch, if this is not the case.
            if type(tmp2) != dict:
                warn_conflict(tmp2, k, f'<...>.{subkey}.{conflict_key}')
                tmp2 = tmp[subkey.strip()] = {conflict_key: tmp2}

            tmp = tmp2

        final = final.strip()
        if final in tmp:
            # If all keys are consistent, the last subkey should not have been previously used.
            # Apply a patch, if this is not the case.
            warn_conflict(v, k, f'{k}.{conflict_key}')
            tmp[final][conflict_key] = v
        else:
            tmp[final] = v

    return result

def get_from_nested_dict(
        nested_dict: dict,
        nested_keys: list[str],
        default: Any = dict()
    ) -> Any:
    """
    Get data from nested dict.
    """
    if 0 == len(nested_keys):
        raise RuntimeError('no nested keys provided')
    elif 1 == len(nested_keys):
        return nested_dict.get(nested_keys[0], default)
    else:
        nd = nested_dict.get(nested_keys[0], {})
        return get_from_nested_dict(nd, nested_keys[1:], default)

def create_task_id(
        model_name: str,
        model_tag: str,
        creation_date: datetime
    ) -> str:
    """
    Create a task ID from a model name, model tag, and creation date.

    The task ID is the Base64-encoded plain task ID.
    The plain task ID corresponds to <model-name>:<model-tag>:<creation-date-in-epoch-time>.
    """
    # Check that model name / tag complies with naming rules.
    pattern = re.compile('[a-z0-9][a-z0-9-]+')
    if not pattern.fullmatch(model_name):
        raise RuntimeError('invalid model name')
    if not pattern.fullmatch(model_tag):
        raise RuntimeError('invalid model tag')

    # Concatenate model name, model tag, and creation date.
    plain_task_id = f'{model_name}:{model_tag}:{creation_date.timestamp()}'

    # Encode plain task ID.
    task_id = base64.b64encode(plain_task_id.encode())

    return task_id.decode('utf8')

def decode_task_id(
        task_id: str
    ) -> Tuple[str, str, datetime]:
    """
    Decode a task ID and retrieve the original model name, model tag, and creation date.
    """
    try:
        # Get plain text version of base64-encoded string.
        plain_task_id = base64.b64decode(task_id).decode('utf-8')

        # Extract model name, model tag, and creation date in epoch time (as string).
        model_name, model_tag, str_creation_date_epoch = plain_task_id.split(':')

        # Parse to float.
        creation_date_epoch = float(str_creation_date_epoch)
    except:
        raise RuntimeError('malformed task ID')

    # Convert creation time from epoch time to UTC datetime.
    creation_date = datetime.fromtimestamp(creation_date_epoch, tz=timezone.utc)

    return model_name, model_tag, creation_date

from hashlib import sha1

def container_name(
       model_name: str,
       model_tag: str,
       creation_date: datetime
) -> str:
    """
    Provide a (sufficiently) unique container name from model name, model tag, and creation date.
    """
    m = sha1()
    m.update(model_name.encode())
    m.update(model_tag.encode())
    m.update(creation_date.isoformat().encode())
    return m.hexdigest()
