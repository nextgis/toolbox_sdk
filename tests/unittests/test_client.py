import math

import responses
from responses.matchers import header_matcher

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
    def test_parallel_download_with_multiple_chunks(self, client, tmp_path):
        # Create a larger test content
        test_content = b"chunk" * 1000  # 6000 bytes
        output_file = tmp_path / "output.txt"

        # Configure client for testing
        client.download_manager.config.max_workers = 4
        chunk_size = len(test_content) // 4

        # Mock HEAD request
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={"content-length": str(len(test_content))},
            status=200,
        )

        # Mock chunk requests
        expected_ranges = set()
        for i in range(4):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < 3 else len(test_content) - 1
            expected_ranges.add(f"bytes={start}-{end}")

            responses.add(
                responses.GET,
                f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
                match=[
                    header_matcher({"Range": f"bytes={start}-{end}"}),
                    header_matcher({"Authorization": f"Token {TEST_API_KEY}"}),
                ],
                body=test_content[start : end + 1],
                status=206,
            )

        result = client.download_file(TEST_FILE_ID, output_file)

        # Verify the result
        assert result.exists()
        assert result.read_bytes() == test_content

        # Verify requests
        print(responses.calls)
        assert len(responses.calls) == 6  # HEAD + HEAD + 4 GET requests
        assert responses.calls[0].request.method == "HEAD"
        assert responses.calls[1].request.method == "HEAD"

        # Verify each chunk request (in any order)
        actual_ranges = set()
        for call in responses.calls[2:]:  # Skip HEAD request
            assert call.request.method == "GET"
            assert "Range" in call.request.headers
            actual_ranges.add(call.request.headers["Range"])

        # Verify that all expected ranges were requested
        assert actual_ranges == expected_ranges

        # Additional verification that each range was requested exactly once
        range_counts = {}
        for call in responses.calls[2:]:
            range_header = call.request.headers["Range"]
            range_counts[range_header] = range_counts.get(range_header, 0) + 1

        # Verify each range was requested exactly once
        assert all(
            count == 1 for count in range_counts.values()
        ), "Some ranges were requested multiple times"

    @responses.activate
    def test_simple_download_no_parallel(self, client, tmp_path):
        test_content = b"test content"

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

        # Mock simple GET request
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            body=test_content,
            status=200,
        )

        result = client.download_file(TEST_FILE_ID, tmp_path, use_parallel=False)

        # Verify the result
        assert result.exists()
        assert result.read_bytes() == test_content

        # Verify only one request was made
        assert len(responses.calls) == 2
        assert responses.calls[0].request.method == "HEAD"
        assert responses.calls[1].request.method == "GET"
        assert "Range" not in responses.calls[0].request.headers

    @responses.activate
    def test_parallel_download_edge_cases(self, client, tmp_path):
        # Test with content size that doesn't divide evenly
        test_content = b"chunk" * 999  # 5994 bytes (not divisible by 4)
        output_file = tmp_path / "output.txt"

        # Configure client for testing
        client.download_manager.config.max_workers = 4
        chunk_size = math.ceil(len(test_content) / 4)

        # Mock HEAD request
        responses.add(
            responses.HEAD,
            f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
            headers={"content-length": str(len(test_content))},
            status=200,
        )

        # Mock chunk requests
        expected_ranges = set()
        for i in range(4):
            start = i * chunk_size
            end = min(start + chunk_size - 1, len(test_content) - 1)
            expected_ranges.add(f"bytes={start}-{end}")

            responses.add(
                responses.GET,
                f"{TEST_BASE_URL}/api/download/{TEST_FILE_ID}",
                match=[
                    responses.matchers.header_matcher({"Range": f"bytes={start}-{end}"})
                ],
                body=test_content[start : end + 1],
                status=206,
            )

        result = client.download_file(TEST_FILE_ID, output_file)

        # Verify the result
        assert result.exists()
        assert result.read_bytes() == test_content

        # Verify ranges
        actual_ranges = {
            call.request.headers["Range"]
            for call in responses.calls[1:]
            if call.request.method == "GET"
        }
        assert actual_ranges == expected_ranges
