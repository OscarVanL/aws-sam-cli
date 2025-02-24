from unittest import TestCase
from mock import Mock, patch, call

from samcli.lib.utils.tar import create_tarball


class TestTar(TestCase):
    @patch("samcli.lib.utils.tar.tarfile.open")
    @patch("samcli.lib.utils.tar.TemporaryFile")
    def test_generating_tarball(self, temporary_file_patch, tarfile_open_patch):
        temp_file_mock = Mock()
        temporary_file_patch.return_value = temp_file_mock

        tarfile_file_mock = Mock()
        tarfile_open_patch.return_value.__enter__.return_value = tarfile_file_mock

        with create_tarball({"/some/path": "/layer1", "/some/dockerfile/path": "/Dockerfile"}) as acutal:
            self.assertEquals(acutal, temp_file_mock)

        tarfile_file_mock.add.assert_called()
        tarfile_file_mock.add.assert_has_calls(
            [call("/some/path", arcname="/layer1"), call("/some/dockerfile/path", arcname="/Dockerfile")],
            any_order=True,
        )

        temp_file_mock.flush.assert_called_once()
        temp_file_mock.seek.assert_called_once_with(0)
        temp_file_mock.close.assert_called_once()
        tarfile_open_patch.assert_called_once_with(fileobj=temp_file_mock, mode="w")
