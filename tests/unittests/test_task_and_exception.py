import pytest
import responses

from toolbox_sdk import Task, ToolboxAPIError, ToolboxError, ToolboxTimeoutError

from conftest import TEST_BASE_URL, TEST_TASK_ID, TEST_TOOL_NAME


class TestTool:
    @responses.activate
    def test_tool_submit(self, client):
        tool = client.tool(TEST_TOOL_NAME)
        inputs = {"param": "value"}

        responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/api/json/execute/",
            json={"task_id": TEST_TASK_ID},
            status=200,
        )

        task = tool.submit(inputs)
        assert isinstance(task, Task)
        assert task.task_id == TEST_TASK_ID

    @responses.activate
    def test_tool_sync_execution(self, client):
        tool = client.tool(TEST_TOOL_NAME)
        inputs = {"param": "value"}

        # Mock task submission
        responses.add(
            responses.POST,
            f"{TEST_BASE_URL}/api/json/execute/",
            json={"task_id": TEST_TASK_ID},
            status=200,
        )

        # Mock task status checks
        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/json/status/{TEST_TASK_ID}/",
            json={"state": "SUCCESS", "output": {"result": "value"}},
            status=200,
        )

        result = tool(inputs)
        assert result.task_id == TEST_TASK_ID
        assert result.state == "SUCCESS"
        assert result.outputs == {"result": "value"}


class TestTask:
    @responses.activate
    def test_check_status(self, client):
        task = Task(client, TEST_TASK_ID)

        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/json/status/{TEST_TASK_ID}/",
            json={"state": "RUNNING"},
            status=200,
        )

        status = task.check_status()
        assert status["state"] == "RUNNING"

    @responses.activate
    def test_wait_for_completion_success(self, client):
        task = Task(client, TEST_TASK_ID)

        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/json/status/{TEST_TASK_ID}/",
            json={"state": "SUCCESS", "output": {"result": "value"}},
            status=200,
        )

        result = task.wait_for_completion(timeout=1)
        assert result.state == "SUCCESS"
        assert result.outputs == {"result": "value"}

    @responses.activate
    def test_wait_for_completion_timeout(self, client):
        task = Task(client, TEST_TASK_ID)

        responses.add(
            responses.GET,
            f"{TEST_BASE_URL}/api/json/status/{TEST_TASK_ID}/",
            json={"state": "RUNNING"},
            status=200,
        )

        with pytest.raises(ToolboxTimeoutError):
            task.wait_for_completion(timeout=0.1, poll_interval=0.05)


def test_error_handling():
    """Test error handling and custom exceptions"""
    with pytest.raises(ToolboxError):
        raise ToolboxError("Test error")

    with pytest.raises(ToolboxAPIError):
        raise ToolboxAPIError("API error")

    with pytest.raises(ToolboxTimeoutError):
        raise ToolboxTimeoutError("Timeout error")
