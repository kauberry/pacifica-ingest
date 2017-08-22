"""Index server unit and integration tests."""
import unittest
from tempfile import NamedTemporaryFile
import requests
from ingest.orm import IngestState, BaseModel, update_state, read_state
from ingest.utils import get_unique_id, get_job_id
from ingest.tarutils import open_tar
from ingest.tarutils import MetaParser
from ingest.tarutils import TarIngester
from ingest.tarutils import FileIngester
from ingest.backend.tasks import ingest
from playhouse.test_utils import test_database
from peewee import SqliteDatabase


TEMP_DB = NamedTemporaryFile()
TEST_DB = SqliteDatabase(TEMP_DB.name)


class IndexServerUnitTests(unittest.TestCase):
    """Index server unit and integration tests."""

    def test_file_ingester(self):
        """Test the FileIngester class."""
        FileIngester('sha1', 'fakehashsum', '127.0.0.1', '1')
        hit_exception = False
        try:
            FileIngester('badfunc', 'fakehashsum', '127.0.0.1', '1')
        except ValueError:
            hit_exception = True
        self.assertTrue(hit_exception)

    def test_load_meta(self):
        """Test sucking metadata from uploader and configuring it in a dictionary suitable to blob to meta ingest."""
        tar = open_tar('test_data/good.tar')

        meta = MetaParser()
        meta.load_meta(tar, 1)
        self.assertTrue(meta)

    def test_tasks(self):
        """Test the ingest task."""
        job_id = get_unique_id(1, 'upload_job')

        ingest(job_id, 'test_data/good.tar')
        self.assertTrue(job_id)

    def test_post_metadata(self):
        """Test sucking metadata from uploader and configuring it in a dictionary suitable to blob to meta ingest."""
        tar = open_tar('test_data/good.tar')
        meta = MetaParser()
        meta.load_meta(tar, 1)
        success, exception = meta.post_metadata()
        self.assertTrue(success)
        self.assertFalse(exception)
        tar = open_tar('test_data/bad-mimetype.tar')
        meta = MetaParser()
        meta.load_meta(tar, 2)
        success, exception = meta.post_metadata()
        self.assertFalse(success)
        self.assertTrue(exception)

    def test_down_metadata(self):
        """Test a failed upload of the metadata."""
        tar = open_tar('test_data/good.tar')
        meta = MetaParser()

        def bad_put(*args, **kwargs):  # pylint: disable=unused-argument
            """bad put to the metadata server."""
            raise requests.HTTPError()
        meta.session.put = bad_put
        meta.load_meta(tar, 1)
        success, exception = meta.post_metadata()
        self.assertFalse(success)
        self.assertTrue(exception)

    def test_ingest_tar(self):
        """Test moving individual files to the archive files are validated inline with the upload."""
        tar = open_tar('test_data/good.tar')
        meta = MetaParser()
        meta.load_meta(tar, 1)

        tingest = TarIngester(tar, meta)
        # validate archive process

        # if not valid:
        #     rollback()
        # success = MetaUpload()
        tingest.ingest()
        self.assertTrue(tingest)

    def test_update_state(self):
        """Test return and update of unique index."""
        with test_database(TEST_DB, (BaseModel, IngestState)):
            test_object = IngestState.create(job_id=999, state='ERROR', task='unbundling',
                                             task_percent=42.3)
            self.assertEqual(test_object.job_id, 999)
            IngestState.database_close()
            update_state(999, 'WORKING', 'validating', 33.2)
            record = read_state(999)
            self.assertEqual(record.state, 'WORKING')
            self.assertEqual(record.task, 'validating')
            self.assertEqual(float(record.task_percent), 33.2)
            record = read_state(None)
            self.assertEqual(record.state, 'DATA_ACCESS_ERROR')
            self.assertEqual(record.task, 'read_state')
            self.assertEqual(record.task_percent, 0)

    def test_get_job_id(self):
        """Parse the parameters for a request from the environ dictionary."""
        environ = {'QUERY_STRING': 'job_id=100'}
        job_id = get_job_id(environ)
        self.assertEqual(job_id, 100)
