import math

import pytest
import responses

from toolbox_sdk import DownloadConfig, ToolboxClient

TEST_API_KEY = "test-api-key"
TEST_BASE_URL = "https://toolbox.example.com"
TEST_TOOL_NAME = "convert"
TEST_TASK_ID = "test-task-id"
TEST_FILE_ID = "test-file-id"


def add_download_mocks(
    rsps,
    url: str,
    content: bytes,
    workers: int = 2,
    include_simple_get: bool = True,
):
    """Helper function to add all necessary download-related mocks"""
    content_length = len(content)

    # Add HEAD request mock
    rsps.add(
        responses.HEAD,
        url,
        headers={"content-length": str(content_length)},
        status=200,
    )

    # Calculate chunk sizes and boundaries
    chunk_size = math.ceil(content_length / workers)
    chunks = []

    # Create non-overlapping chunks
    for i in range(workers):
        start = i * chunk_size
        end = min((i + 1) * chunk_size - 1, content_length - 1)
        chunk_content = content[start : end + 1]
        chunks.append((start, end, chunk_content))

    # Add range request mocks for parallel download first
    for start, end, chunk_content in chunks:
        rsps.add(
            responses.GET,
            url,
            match=[
                responses.matchers.header_matcher({"Range": f"bytes={start}-{end}"})
            ],
            body=chunk_content,
            status=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{content_length}",
                "Content-Length": str(len(chunk_content)),
            },
        )

    # Add regular GET request mock for non-parallel download if included
    if include_simple_get:
        rsps.add(responses.GET, url, body=content, status=200)


@pytest.fixture
def client():
    """Create a ToolboxClient instance for testing"""
    return ToolboxClient(api_key=TEST_API_KEY, base_url=TEST_BASE_URL)


@pytest.fixture
def download_config():
    """Create a DownloadConfig instance for testing"""
    return DownloadConfig(
        chunk_size=1024,
        max_workers=2,
        use_parallel=True,
        verify_hash=True,
        max_retries=2,
        backoff_factor=0.1,
    )


@pytest.fixture
def mock_session():
    """Fixture to provide a session with responses activated"""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def test_content():
    """Fixture to provide test content of various sizes"""
    return {
        "small": b"small content",
        "medium": b"medium content" * 100,
        "large": b"large content" * 1000,
        "empty": b"",
        "single": b"x",
    }
