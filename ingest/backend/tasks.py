#!/usr/bin/python
"""Module that contains all the amqp tasks that support the ingest infrastructure."""
from __future__ import absolute_import, print_function
# from time import sleep
import os
import traceback
import requests
# from ingest.orm import IngestState, BaseModel, update_state, read_state
# from ingest.utils import get_job_id
# from ingest import tarutils
from ingest.tarutils import open_tar
from ingest.tarutils import MetaParser
from ingest.tarutils import TarIngester
from ingest.orm import update_state
from celery import current_task
from .celery_ingest import INGEST_APP


class IngestException(Exception):
    """Ingest class exception."""

    pass


def ingest_check_tarfile(job_id, filepath):
    """Check the ingest tarfile and return state or set it properly."""
    update_state(job_id, 'OK', 'Open tar', 0)
    tar = open_tar(filepath)
    if tar is None:
        update_state(job_id, 'FAILED', 'Bad tarfile', 0)
        raise IngestException()
    update_state(job_id, 'OK', 'Open tar', 100)
    return tar


def ingest_metadata_parser(job_id, tar):
    """Ingest the metadata and set the state appropriately."""
    update_state(job_id, 'OK', 'load metadata', 0)
    meta = MetaParser()
    try:
        meta.load_meta(tar, job_id)
    # pylint: disable=broad-except
    except Exception as ex:
        update_state(job_id, 'FAILED', 'load metadata', 0, str(ex))
        raise IngestException()
    update_state(job_id, 'OK', 'load metadata', 100)
    return meta


def ingest_policy_check(job_id, meta_str):
    """Ingest check to validate metadata at policy."""
    success, exception = validate_meta(meta_str)
    if not success:
        update_state(job_id, 'FAILED', 'Policy Validation', 0, exception)
        raise IngestException()
    update_state(job_id, 'OK', 'Policy Validation', 100)


def ingest_files(job_id, ingest_obj):
    """Ingest the files to the archive interface."""
    update_state(job_id, 'OK', 'ingest files', 0)
    try:
        ingest_obj.ingest()
    # pylint: disable=broad-except
    except Exception as ex:
        # rollback files
        stack_dump = traceback.format_exc()
        update_state(job_id, 'FAILED', 'ingest files', 0, u'{}\n{}'.format(stack_dump, str(ex)))
        raise IngestException()
    update_state(job_id, 'OK', 'ingest files', 100)


def ingest_metadata(job_id, meta):
    """Ingest metadata to the metadata service."""
    update_state(job_id, 'OK', 'ingest metadata', 0)
    success, exception = meta.post_metadata()
    if not success:
        # rollback files
        update_state(job_id, 'FAILED', 'ingest metadata', 0, str(exception))
        raise IngestException()
    update_state(job_id, 'OK', 'ingest metadata', 100)


@INGEST_APP.task(ignore_result=False)
def ingest(job_id, filepath):
    """Ingest a tar bundle into the archive."""
    try:
        tar = ingest_check_tarfile(job_id, filepath)
        meta = ingest_metadata_parser(job_id, tar)
        ingest_obj = TarIngester(tar, meta)
        ingest_policy_check(job_id, meta.meta_str)
        ingest_files(job_id, ingest_obj)
        ingest_metadata(job_id, meta)
        tar.close()
        os.unlink(filepath)
    except IngestException:
        return


def validate_meta(meta_str):
    """Validate metadata."""
    try:
        archivei_server = os.getenv('POLICY_SERVER', '127.0.0.1')
        archivei_port = os.getenv('POLICY_PORT', '8181')
        archivei_url = 'http://{0}:{1}/ingest'.format(archivei_server, archivei_port)

        headers = {'content-type': 'application/json'}

        session = requests.session()
        retry_adapter = requests.adapters.HTTPAdapter(max_retries=5)
        session.mount('http://', retry_adapter)
        session.mount('https://', retry_adapter)
        req = session.post(archivei_url, headers=headers, data=meta_str)

        req_json = req.json()
        if req_json['status'] == 'success':
            return True, ''
        return False, req_json['message']
    # pylint: disable=broad-except
    except Exception as ex:
        return False, ex
    # pylint: enable=broad-except


@INGEST_APP.task(ignore_result=False)
def ping():  # pragma: no cover
    """Check to see if the celery task process is started."""
    print('Pinged!')
    current_task.update_state(state='PING', meta={'Status': 'Background process is alive'})
    print('updated ping status')
