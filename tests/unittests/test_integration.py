import responses

from conftest import TEST_BASE_URL, TEST_FILE_ID, TEST_TASK_ID, add_download_mocks


class TestIntegration:
    def test_full_workflow(self, client, tmp_path):
        """Test the full workflow of uploading, processing, and downloading"""
        # Create test input file
        input_file = tmp_path / "input.txt"
        input_file.write_text("test content")
        test_output_content = b"processed content"

        # Mock all API calls
        with responses.RequestsMock() as rsps:
            # Mock file upload
            rsps.add(
                responses.POST,
                f"{TEST_BASE_URL}/api/upload/?filename=input.txt",
                body=TEST_FILE_ID,
                status=200,
            )

            # Mock tool execution
            rsps.add(
                responses.POST,
                f"{TEST_BASE_URL}/api/json/execute/",
                json={"task_id": TEST_TASK_ID},
                status=200,
            )

            # Mock status check
            rsps.add(
                responses.GET,
                f"{TEST_BASE_URL}/api/json/status/{TEST_TASK_ID}/",
                json={"state": "SUCCESS", "output": {"file": "result-file-id"}},
                status=200,
            )

            # Use helper function to add download-related mocks without the simple GET
            add_download_mocks(
                rsps,
                f"{TEST_BASE_URL}/api/download/result-file-id",
                test_output_content,
                workers=4,  # Use fixed number of workers for predictability
                include_simple_get=False,  # Do not add the regular GET request
            )

            # Execute workflow
            tool_instance = client.tool("test-tool")
            file_id = client.upload_file(input_file)
            result = tool_instance({"input": file_id})
            output_file = tmp_path / "output.txt"
            downloaded_file = client.download_file(
                result.outputs["file"], output_file, use_parallel=True
            )

            # Verify results
            assert downloaded_file.exists()
            assert downloaded_file.read_bytes() == test_output_content

            # Verify all expected requests were made
            expected_calls = 5 + client.download_manager.config.max_workers
            # 5 = upload + execute + status + HEAD + HEAD, plus GET requests workers
            assert len(rsps.calls) == expected_calls

            # Verify request sequence
            assert rsps.calls[0].request.method == "POST"  # Upload
            assert rsps.calls[1].request.method == "POST"  # Execute
            assert rsps.calls[2].request.method == "GET"  # Status
            assert rsps.calls[3].request.method == "HEAD"  # File size check
            assert rsps.calls[4].request.method == "HEAD"  # File size check

            for call in rsps.calls[5:]:
                assert call.request.method == "GET"  # Chunk downloads
                assert "Range" in call.request.headers
