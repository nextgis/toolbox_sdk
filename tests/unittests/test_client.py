import responses

from toolbox_sdk import Tool

from conftest import TEST_API_KEY, TEST_BASE_URL, TEST_FILE_ID, TEST_TOOL_NAME


class TestToolboxClient:
    @responses.activate
    def test_init_client(self, client):
        assert client.base_url == TEST_BASE_URL
        assert client.headers["Authorization"] == f"Token {TEST_API_KEY}"
        assert client.headers["User-Agent"].startswith("NextGIS-Toolbox-SDK/")
        assert client.session is not None

    def test_tool_creation(self, client):
        tool = client.tool(TEST_TOOL_NAME)
        assert isinstance(tool, Tool)
        assert tool.name == TEST_TOOL_NAME
        assert tool.client == client

    @responses.activate
    def test_upload_file(self, client, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/api/upload/?filename=test.txt",
            body=TEST_FILE_ID,
            status=200,
        )

        file_id = client.upload_file(test_file)
        assert file_id == TEST_FILE_ID
        assert len(responses.calls) == 1

    @responses.activate
    def test_download_file(self, client, tmp_path):
        test_content = b"test content"
        output_file = tmp_path / "output.txt"

        # Mock HEAD request
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={
                "content-length": str(len(test_content)),
                "content-disposition": 'attachment; filename="test_file.txt"'
            },
            status=200,
        )

        # Mock GET request
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            body=test_content,
            status=200,
        )

        result = client.download_file(TEST_FILE_ID, output_file)

        # Verify the result
        assert result.exists()
        assert result.read_bytes() == test_content

        # Verify requests
        assert len(responses.calls) == 2  # HEAD + GET
        assert responses.calls[0].request.method == "HEAD"
        assert responses.calls[1].request.method == "GET"
        assert "Range" not in responses.calls[1].request.headers

    @responses.activate
    def test_download_with_content_disposition(self, client, tmp_path):
        test_content = b"test content"

        # Mock HEAD request with content-disposition
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={
                "content-length": str(len(test_content)),
                "content-disposition": 'attachment; filename="test_file.txt"'
            },
            status=200,
        )

        # Mock GET request
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            body=test_content,
            status=200,
        )

        # Download to a directory
        result = client.download_file(TEST_FILE_ID, tmp_path)

        # Verify the result
        assert result.exists()
        assert result.read_bytes() == test_content
        assert result.name == "test_file.txt"  # Should use filename from content-disposition

    @responses.activate
    def test_download_with_task_result_registration(self, client, tmp_path):
        from toolbox_sdk import TaskResult

        test_content = b"test content"

        # Create a task result
        task_result = TaskResult(
            outputs=[
                {
                    "name": "output_file",
                    "title": "Output File",
                    "type": "file",
                    "value": TEST_FILE_ID
                }
            ],
            task_id="test-task-id",
            state="SUCCESS"
        )

        # Mock HEAD request
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={
                "content-length": str(len(test_content)),
                "content-disposition": 'attachment; filename="result.txt"'
            },
            status=200,
        )

        # Mock GET request
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            body=test_content,
            status=200,
        )

        # Download with task result registration
        result = client.download_file(
            TEST_FILE_ID,
            tmp_path,
            output_name="output_file",
            task_result=task_result
        )

        # Verify file was downloaded
        assert result.exists()
        assert result.read_bytes() == test_content

        # Verify task result registration
        assert task_result.get_file_path("output_file") == result
        assert task_result.get_file_path_as_string("output_file") == str(result)
