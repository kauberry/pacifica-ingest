#!/usr/bin/python
"""Test ingest."""
from collections import namedtuple
from datetime import datetime
import mock
import peewee
from ingest.orm import create_tables, IngestState
from ingest.utils import get_job_id, valid_request, create_invalid_return, create_return_params, create_state_return


@mock.patch.object(IngestState, 'table_exists')
def test_bad_db_connection(mock_is_table_exists):
    """Test a failed db connection."""
    mock_is_table_exists.side_effect = peewee.OperationalError(mock.Mock(), 'Error')
    hit_exception = False
    try:
        create_tables(18)
    except peewee.OperationalError:
        hit_exception = True
    assert hit_exception


def test_bad_form_get_job_id():
    """Test the get_job_id methods."""
    environ = {
        'QUERY_STRING': 'job_id=foo'
    }
    chk = get_job_id(environ)
    assert chk[0] is None
    assert chk[1] is None


def test_no_get_job_id():
    """Test the get_job_id methods."""
    environ = {
        'QUERY_STRING': ''
    }
    chk = get_job_id(environ)
    assert chk[0] is None
    assert chk[1] is None


def test_valid_request():
    """Test the valid request method."""
    environ = {
        'QUERY_STRING': '',
        'PATH_INFO': '/blah'
    }
    assert not valid_request(environ)


def test_invalid_return():
    """Test the invalid return method."""
    chk = create_invalid_return()
    assert chk[0] == '404 NOT FOUND'
    assert len(chk[1]) == 2
    assert chk[2] == 'Invalid'


def test_create_return_params():
    """Test the create return params."""
    chk = create_return_params('foo')
    assert chk[0] == '200 OK'
    assert len(chk[1]) == 2
    assert chk[2] == 'foo'


def test_create_state_return():
    """Test the create_state_return method."""
    record = namedtuple('Record', ['job_id', 'state', 'task', 'task_percent', 'updated', 'created', 'exception'])
    rec = record(1, 'test state', 'test task', '12.345', datetime.utcnow(), datetime.utcnow(), '')
    chk = create_state_return(rec)
    assert chk[0] == '200 OK'
    assert len(chk[1]) == 2
    assert len(chk[2]) == 182
