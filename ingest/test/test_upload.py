#!/usr/bin/python
"""Test ingest with good uploads of good and bad data."""
from __future__ import print_function
import requests
from ingest.test import try_good_upload


def test_bad_job_id():
    """Test a bad job ID."""
    req = requests.get('http://127.0.0.1:8066/get_state?job_id=12345')
    assert req.status_code == 404


def test_good_upload():
    """Test the good upload."""
    try_good_upload('good', 'OK', 'ingest metadata', 100)


def test_bad_proposal_upload():
    """Test if the metadata is down."""
    try_good_upload('bad-proposal', 'FAILED', 'Policy Validation', 0)


def test_bad_hashsum_upload():
    """Test if the metadata is down."""
    try_good_upload('bad-hashsum', 'FAILED', 'ingest files', 0)


def test_bad_metadata_upload():
    """Test if the metadata is down."""
    try_good_upload('bad-mimetype', 'FAILED', 'ingest metadata', 0)


def test_bad_json_upload():
    """Test if the metadata is down."""
    try_good_upload('bad-json', 'FAILED', 'load metadata', 0)


def test_bad_tarfile_upload():
    """Test if the metadata is down."""
    try_good_upload('bad-tarfile', 'FAILED', 'Bad tarfile', 0)
