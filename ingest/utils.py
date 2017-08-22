#!/usr/bin/python
"""Testable utilities for ingest."""
from __future__ import print_function
import os
from urlparse import parse_qs
import json
import requests


def get_job_id(environ):
    """Parse the parameters for a request from the environ dictionary."""
    try:
        args = parse_qs(environ['QUERY_STRING'])
        if args:
            job_id = int(args.get('job_id', [''])[0])
            return job_id
        return (None, None)
    # pylint: disable=broad-except
    except Exception:
        return (None, None)
    # pylint: enable=broad-except


def valid_request(environ):
    """Catch and handle bogus requests (ex. faveicon)."""
    info = environ['PATH_INFO']
    return info == '/get_state'


def create_invalid_return():
    """Create an error message."""
    status = '404 NOT FOUND'
    response_body = 'Invalid'
    response_headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ]
    return (status, response_headers, response_body)


def create_return_params(response_body):
    """Create return parameters."""
    status = '200 OK'
    response_headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ]
    return (status, response_headers, response_body)


def create_state_response(record):
    """Create the state response body from a record."""
    state = {
        'job_id': record.job_id,
        'state': record.state,
        'task': record.task,
        'task_percent': str(record.task_percent),
        'updated': str(record.updated),
        'created': str(record.created),
        'exception': str(record.exception)
    }
    return json.dumps(state)


def create_state_return(record):
    """Create the dictionary containing the start and stop index packs the message components."""
    response_body = create_state_response(record)
    return create_return_params(response_body)


def get_unique_id(id_range, mode):
    """Return a unique job id from the id server."""
    uniqueid_server = os.getenv('UNIQUEID_SERVER', '127.0.0.1')
    uniqueid_port = os.getenv('UNIQUEID_PORT', '8051')

    url = 'http://{0}:{1}/getid?range={2}&mode={3}'.format(uniqueid_server, uniqueid_port, id_range, mode)

    req = requests.get(url)
    body = req.text
    info = json.loads(body)
    unique_id = info['startIndex']

    return unique_id


def receive(environ, job_id):
    """Receive the tar file and save it locally."""
    if environ['REQUEST_METHOD'] == 'POST':
        root = os.getenv('VOLUME_PATH', '/tmp')
        name = str(job_id) + '.tar'
        name = os.path.join(root, name)
        file_out = open(name, 'wb')
        block_size = 1024 * 1024
        content_length = int(environ['CONTENT_LENGTH'])
        while content_length > 0:
            # this needs a file larger than 1M to be part of the tar...
            if content_length > block_size:  # pragma: no cover
                buf = environ['wsgi.input'].read(block_size)
            else:
                buf = environ['wsgi.input'].read(content_length)

            file_out.write(buf)
            content_length -= len(buf)
        file_out.close()
        return name
