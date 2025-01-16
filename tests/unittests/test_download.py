import responses

from toolbox_sdk import DownloadManager

from conftest import TEST_BASE_URL, add_download_mocks


class TestDownloadManager:
    def test_init(self, client, download_config):
        manager = DownloadManager(client, download_config)
        assert manager.client == client
        assert manager.config == download_config

    @responses.activate
    def test_simple_download(self, client, tmp_path):
        manager = DownloadManager(client)
        test_content = b"test content"
        output_file = tmp_path / "output.txt"

        # For simple download, we only need the basic GET mock
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/test.txt",
            body=test_content,
            status=200,
        )

        result = manager._simple_download(f"{TEST_BASE_URL}/test.txt", output_file)
        assert result.exists()
        assert result.read_bytes() == test_content

    @responses.activate
    def test_parallel_download(self, client, tmp_path, download_config):
        manager = DownloadManager(client, download_config)
        test_content = b"test content"
        output_file = tmp_path / "output.txt"

        # Use helper function to add all download-related mocks
        add_download_mocks(
            responses,
            f"{TEST_BASE_URL}/test.txt",
            test_content,
            workers=2,  # Use fixed number of workers
        )

        result = manager._parallel_download(
            f"{TEST_BASE_URL}/test.txt",
            output_file,
        )

        # Verify the result
        assert result.exists()
        assert result.read_bytes() == test_content
