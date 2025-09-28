import responses

from conftest import TEST_BASE_URL, TEST_FILE_ID


class TestDownload:
    @responses.activate
    def test_simple_download(self, client, tmp_path):
        test_content = b"test content"
        output_file = tmp_path / "output.txt"

        # Mock HEAD request to get content length and filename
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={
                "content-length": str(len(test_content)),
                "content-disposition": 'attachment; filename="test_file.txt"'
            },
            status=200,
        )

        # Mock the GET request for the file download
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            body=test_content,
            status=200,
        )

        result = client.download_file(TEST_FILE_ID, output_file)
        assert result.exists()
        assert result.read_bytes() == test_content
        assert result.name == "output.txt"  # When destination is a file path, use that filename

    @responses.activate
    def test_simple_download_2(self, client, tmp_path):
        test_content = b"test content"

        # Mock HEAD request to get content length and filename
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={
                "content-length": str(len(test_content)),
                "content-disposition": 'attachment; filename="test_file.txt"'
            },
            status=200,
        )

        # Mock the GET request for the file download
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            body=test_content,
            status=200,
        )

        # Download to a directory instead of a specific file
        result = client.download_file(TEST_FILE_ID, tmp_path)
        assert result.exists()
        assert result.read_bytes() == test_content
        assert result.name == "test_file.txt"  # Verify filename from content-disposition

    @responses.activate
    def test_download_with_custom_filename(self, client, tmp_path):
        test_content = b"test content"
        output_file = tmp_path / "custom_name.txt"

        # Mock HEAD request without content-disposition
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={"content-length": str(len(test_content))},
            status=200,
        )

        # Mock the GET request
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            body=test_content,
            status=200,
        )

        result = client.download_file(TEST_FILE_ID, output_file)
        assert result.exists()
        assert result.read_bytes() == test_content
        assert result.name == "custom_name.txt"  # Should use the provided filename

    @responses.activate
    def test_download_with_task_result_registration(self, client, tmp_path):
        from toolbox_sdk import TaskResult

        test_content = b"test content"
        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

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
            output_dir,
            output_name="output_file",
            task_result=task_result
        )

        # Verify file was downloaded
        assert result.exists()
        assert result.read_bytes() == test_content

        # Verify task result registration
        assert task_result.get_file_path("output_file") == result
        assert task_result.get_file_path_as_string("output_file") == str(result)

    @responses.activate
    def test_download_results(self, client, tmp_path):
        from toolbox_sdk import TaskResult

        test_content = b"test content"
        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        # Create a task result with multiple file outputs
        task_result = TaskResult(
            outputs=[
                {
                    "name": "file1",
                    "title": "File 1",
                    "type": "file",
                    "value": f"{TEST_FILE_ID}_1"
                },
                {
                    "name": "file2",
                    "title": "File 2",
                    "type": "file",
                    "value": f"{TEST_FILE_ID}_2"
                },
                {
                    "name": "text",
                    "title": "Text Output",
                    "type": "unicode",
                    "value": "Some text"
                }
            ],
            task_id="test-task-id",
            state="SUCCESS"
        )

        # Mock HEAD and GET requests for both files
        for i in range(1, 3):
            file_id = f"{TEST_FILE_ID}_{i}"

            # Mock HEAD request
            responses.add(
                responses.HEAD,
                f"{TEST_BASE_URL}/api/download/{file_id}",
                headers={
                    "content-length": str(len(test_content)),
                    "content-disposition": f'attachment; filename="result{i}.txt"'
                },
                status=200,
            )

            # Mock GET request
            responses.add(
                responses.GET,
                f"{TEST_BASE_URL}/api/download/{file_id}",
                body=test_content,
                status=200,
            )

        # Download all results
        result = client.download_results(task_result, output_dir)

        # Verify all files were downloaded and registered
        assert result.get_file_path("file1").exists()
        assert result.get_file_path("file2").exists()
        assert result.get_file_path("file1").read_bytes() == test_content
        assert result.get_file_path("file2").read_bytes() == test_content

        # Verify non-file outputs are not affected
        assert result["text"] == "Some text"
        assert result.get_file_path("text") is None

        # Verify we can get all file paths
        all_paths = result.get_all_file_paths()
        assert len(all_paths) == 2
        assert "file1" in all_paths
        assert "file2" in all_paths
