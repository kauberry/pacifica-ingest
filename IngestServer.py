#!/usr/bin/env python
"""Ingest Server Main."""
import os
import sys
import signal
import logging
from wsgiref.simple_server import make_server
import peewee
from ingest.orm import IngestState, read_state, update_state, create_tables
from ingest.utils import create_invalid_return, create_state_return, \
                            get_unique_id, get_job_id, receive, create_state_response
from ingest.backend import tasks


# pylint: disable=unused-argument
def exit_handler(signum, frame):
    """Catch term and exit cleanly."""
    print 'Exiting cleanly from {0}'.format(signum)
    sys.exit(signum)
# pylint: enable=unused-argument


signal.signal(signal.SIGTERM, exit_handler)


def start_ingest(job_id, filepath):
    """Start the celery injest task."""
    tasks.ingest.delay(job_id, filepath)


def application(environ, start_response):
    """The wsgi callback."""
    create_tables()
    info = environ['PATH_INFO']
    if info and info == '/get_state':
        job_id = get_job_id(environ)
        try:
            record = read_state(job_id)
        except peewee.DoesNotExist:
            status, response_headers, response_body = create_invalid_return()
            start_response(status, response_headers)
            return [response_body]
        if record:
            status, response_headers, response_body = create_state_return(record)
            start_response(status, response_headers)
            return [response_body]
    elif info and info == '/upload':

        # celery_is_alive = ping_celery()

        celery_is_alive = True
        if celery_is_alive:
            # get temporary id from id server
            job_id = get_unique_id(1, 'upload_job')
            update_state(job_id, 'OK', 'UPLOADING', 0)

            try:
                filepath = receive(environ, job_id)
            # pylint: disable=broad-except
            except Exception as exc:
                update_state(job_id, 'FAILED', 'receive bundle', 0, str(exc))
                status = '500 Internal Server Error'
                record = read_state(job_id)
                response_body = create_state_response(record)
                response_headers = [
                    ('Content-Type', 'application/json'),
                    ('Content-Length', str(len(response_body)))
                ]
                start_response(status, response_headers)
                return [response_body]
            # pylint: enable=broad-except

            if filepath != '':
                start_ingest(job_id, filepath)

            record = read_state(job_id)

        else:
            record = IngestState()
            record.state = 'ERROR: Celery is dead'
            record.job_id = -99

        if record:
            status, response_headers, response_body = create_state_return(record)
            start_response(status, response_headers)
            return [response_body]

    else:
        status, response_headers, response_body = create_invalid_return()
        start_response(status, response_headers)
        return [response_body]

    status, response_headers, response_body = create_invalid_return()
    start_response(status, response_headers)
    return [response_body]


def main():
    """Entry point for main index server."""
    peewee_logger = logging.getLogger('peewee')
    peewee_logger.setLevel(logging.DEBUG)
    peewee_logger.addHandler(logging.StreamHandler())

    main_logger = logging.getLogger('index_server')
    main_logger.setLevel(logging.DEBUG)
    main_logger.addHandler(logging.StreamHandler())

    msg = {'msg': os.getenv('MYSQL_ENV_MYSQL_DATABASE', 'pacifica_ingest')}
    main_logger.info('MYSQL_ENV_MYSQL_DATABASE = %(msg)s', msg)
    msg['msg'] = os.getenv('MYSQL_PORT_3306_TCP_ADDR', '127.0.0.1')
    main_logger.info('MYSQL_PORT_3306_TCP_ADDR = %(msg)s', msg)
    msg['msg'] = os.getenv('MYSQL_PORT_3306_TCP_PORT', '3306')
    main_logger.info('MYSQL_PORT_3306_TCP_PORT = %(msg)s', msg)
    msg['msg'] = os.getenv('MYSQL_ENV_MYSQL_USER', 'ingest')
    main_logger.info('MYSQL_ENV_MYSQL_USER = %(msg)s', msg)
    main_logger.info('MYSQL_ENV_MYSQL_PASSWORD = %(msg)s', msg)
    msg['msg'] = os.getenv('MYSQL_ENV_MYSQL_PASSWORD', 'ingest')

    create_tables()
    httpd = make_server('0.0.0.0', 8066, application)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
