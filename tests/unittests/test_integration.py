import responses

from conftest import TEST_BASE_URL, TEST_FILE_ID, TEST_TASK_ID


class TestIntegration:
    def test_full_workflow(self, client, tmp_path):
        """Test the full workflow of uploading, processing, and downloading"""
        # Create test input file
        input_file = tmp_path / "input.txt"
        input_file.write_text("test content")
        test_output_content = b"processed content"

        # Mock all API calls
        with responses.RequestsMock() as rsps:
            # Mock file upload with JSON response
            rsps.add(
                responses.POST,
                f"{TEST_BASE_URL}/api/upload/?filename=input.txt&format=json",
                json={
                    "name": "input.txt",
                    "local": {"uuid": TEST_FILE_ID.replace("storage/", "")},
                    "s3": None,
                },
                status=200,
            )

            # Mock tool execution
            rsps.add(
                responses.POST,
                f"{TEST_BASE_URL}/api/tasks/",
                json={"task_id": TEST_TASK_ID},
                status=200,
            )

            # Mock status check
            rsps.add(
                responses.GET,
                f"{TEST_BASE_URL}/api/tasks/{TEST_TASK_ID}",
                json={
                    "state": "SUCCESS",
                    "output": [
                        {
                            "name": "file",
                            "title": "Output File",
                            "type": "file",
                            "value": "result-file-id",
                        }
                    ],
                },
                status=200,
            )

            # Mock HEAD request for download
            rsps.add(
                responses.HEAD,
                f"{TEST_BASE_URL}/api/download/result-file-id",
                headers={
                    "content-length": str(len(test_output_content)),
                    "content-disposition": 'attachment; filename="result.txt"',
                },
                status=200,
            )

            # Mock GET request for download
            rsps.add(
                responses.GET,
                f"{TEST_BASE_URL}/api/download/result-file-id",
                body=test_output_content,
                status=200,
            )

            # Execute workflow
            tool_instance = client.tool("test-tool")
            file_id = client.upload_file(input_file)
            result = tool_instance({"input": file_id})
            output_file = tmp_path / "output.txt"
            downloaded_file = client.download_file(result["file"], output_file)

            # Verify results
            assert downloaded_file.exists()
            assert downloaded_file.read_bytes() == test_output_content

            # Verify all expected requests were made
            assert len(rsps.calls) == 5  # upload + execute + status + HEAD + GET

            # Verify request sequence
            assert rsps.calls[0].request.method == "POST"  # Upload
            assert rsps.calls[1].request.method == "POST"  # Execute
            assert rsps.calls[2].request.method == "GET"  # Status
            assert rsps.calls[3].request.method == "HEAD"  # File size check
            assert rsps.calls[4].request.method == "GET"  # Download
