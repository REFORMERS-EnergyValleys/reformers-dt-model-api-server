import connexion
import docker
import docker.models.containers

from ansistrip import ansi_strip
from connexion.problem import problem
from enum import Enum
from datetime import datetime
from dateutil import parser as datetimeparser
from flask import current_app
from typing import Optional, Tuple, Union

from reformers_model_api_server.models.info_create_model import InfoCreateModel  # noqa: E501
from reformers_model_api_server.models.info_model_generator import InfoModelGenerator  # noqa: E501
from reformers_model_api_server.controllers.model_generators_controller import info_model_generator
from reformers_model_api_server.controllers.util import container_name, decode_task_id, get_model_image_labels, get_from_nested_dict
from reformers_model_repo_client.exceptions import NotFoundException

class TaskStatus(str, Enum):
    """
    Status of model generation task.

    :var PENDING: Task has not yet finished.
    :vartype PENDING: Literal['pending']
    :var FINISHED: Task has finished successfully and the new model container image is available in the registry.
    :vartype FINISHED: Literal['finished']
    :var SUPERSEDED: A newer task has generated a model container image that is available in the registry.
    :vartype SUPERSEDED: Literal['superseded']
    :var FAILED: Task has failed and has not generated a new model container image in the registry.
    :vartype FAILED: Literal['failed']
    """
    PENDING = 'pending'
    FINISHED = 'finished'
    SUPERSEDED = 'superseded'
    FAILED = 'failed'

def status_model_creation(
        generator_name: str,
        generator_tag: str,
        task_id: str
    ) -> Union[InfoCreateModel, problem]: # noqa: E501
    """
    Retrieve information about model generation tasks

    :param generator_name: generator name
    :type generator_name: str
    :param generator_tag: generator tag
    :type generator_tag: str
    :param task_id: ID of model generation task
    :type task_id: str
    :rtype: Union[InfoCreateModel, problem]
    """
    try:
        # Get info on model generator.
        info_generator = info_model_generator(generator_name, generator_tag)

        if not type(info_generator) == InfoModelGenerator:
            return info_generator

        model_name, model_tag, task_creation_date = decode_task_id(task_id)

    except Exception as ex:
        return problem(
            title='Bad Request',
            detail=f'Invalid task ID: {ex}',
            status=400,
        )

    try:
        status, info = get_task_status(
            generator_name, generator_tag, model_name, model_tag, task_creation_date
        )

        return InfoCreateModel(
            task_id=task_id, status=status, creation_date=task_creation_date, info=info
        )

    except Exception as ex:
        return problem(
            title='Interal Server Error',
            detail=f'Failed to retrieve task information: {ex}',
            status=500,
        )

def get_task_status(
        generator_name: str,
        generator_tag: str,
        model_name: str,
        model_tag: str,
        task_creation_date: datetime
    ) -> Tuple[TaskStatus, str]:
    """
    Retrieve the status of the model generation task.

    :param generator_name: generator name
    :type generator_name: str
    :param generator_tag: generator tag
    :type generator_tag: str
    :param model_name: model name
    :type model_name: str
    :param model_tag: model tag
    :type model_tag: str
    :param task_creation_date: task creation date
    :type task_creation_date: datetime
    :return: status & info of model generation task
    :rtype: Tuple[TaskStatus, str | None]
    """
    with current_app.app_context():

        remove_containers: bool = current_app.remove_containers

        docker_client = docker.from_env()

        ls = docker_client.containers.list(
            all=True,
            filters=dict(name=container_name(model_name, model_tag, task_creation_date))
            )

        if 1 == len(ls) and 'exited' != ls[0].status:
            # The container is still runnning.
            raw_logs_tail: str = ls[0].logs(tail=1).decode('utf-8') # Get latest output from logs
            logs_tail: str = ansi_strip(raw_logs_tail).strip(' -\n\t') # Remove formatting
            return TaskStatus.PENDING, f'generator is {ls[0].status}, progress: {logs_tail}'
        elif 0 == len(ls) or (1 == len(ls) and 'exited' == ls[0].status):
            try:
                image_labels = get_model_image_labels(
                    generator_name, generator_tag, model_name, model_tag, current_app.repo_client
                )
            except NotFoundException:
                # The container has finished but no model image has been created.
                return TaskStatus.FAILED, get_task_logs(ls, remove_containers)

            generation_parameters = get_from_nested_dict(
                image_labels, [generator_name, generator_tag, model_name, model_tag]
            )

            str_image_creation_date = generation_parameters.get('CREATED')
            if not str_image_creation_date:
                raise RuntimeError('creation date missing in model meta information')

            image_creation_date = datetimeparser.parse(str_image_creation_date)

            if (image_creation_date < task_creation_date):
                # The container has finished, but has failed to generate an updated model image.
                return TaskStatus.FAILED, get_task_logs(ls, remove_containers)
            elif (image_creation_date == task_creation_date):
                # The container has finished, and has generated an updated model image.
                return TaskStatus.FINISHED, get_task_logs(ls, remove_containers)
            else:
                # The container has finished, but an updated model image from a newer task is available.
                # It is not clear whether the task has finished successfully or failed, but ultimately it
                # doesn't matter, because the result has been superseded.
                return TaskStatus.SUPERSEDED, get_task_logs(ls, remove_containers)
        else:
            # Above, all cases for 1 container with a unique ID either running or exited (and probably
            # removed after exiting) are covered. If executions lands here, the task ID was not unique!
            raise RuntimeError('Task ID is not unique')

def get_task_logs(
        containers: list[docker.models.containers.Container],
        remove_containers: bool
    ) -> Optional[str]:
    """
    Get logs from container (if available)

    :param containers: list of container objects
    :type containers: list[Container]:
    :param remove_containers: True if containers are removed after they exit
    :type remove_containers: bool
    :return: container logs
    :rtype: str
    """
    if remove_containers or 0 == len(containers):
        return None

    return containers[0].logs().decode('utf-8')
