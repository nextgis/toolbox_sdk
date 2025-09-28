import pytest
import responses

from toolbox_sdk import DownloadConfig, ToolboxClient

TEST_API_KEY = "test-api-key"
TEST_BASE_URL = "https://toolbox.example.com"
TEST_TOOL_NAME = "convert"
TEST_TASK_ID = "test-task-id"
TEST_FILE_ID = "test-file-id"


@pytest.fixture
def client():
    """Create a ToolboxClient instance for testing"""
    return ToolboxClient(api_key=TEST_API_KEY, base_url=TEST_BASE_URL)


@pytest.fixture
def download_config():
    """Create a DownloadConfig instance for testing"""
    return DownloadConfig(
        chunk_size=1024,
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
