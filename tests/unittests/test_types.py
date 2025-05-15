import json

import pytest

from toolbox_sdk import TaskResult


class TestTaskResult:
    def test_basic_functionality(self):
        """Test basic TaskResult functionality"""
        task_id = "1571686e-bcd6-42e2-a101-5fe270dd7a65"
        state = "SUCCESS"
        tr = TaskResult(
            outputs=[
                {
                    "name": "hello",
                    "title": "hello",
                    "type": "unicode",
                    "value": "Hello, Natalia!",
                }
            ],
            task_id=task_id,
            state=state,
        )
        assert tr.task_id == task_id
        assert tr.state == state
        assert tr.value == "Hello, Natalia!"
        assert tr["hello"] == "Hello, Natalia!"

    def test_multiple_outputs(self):
        """Test TaskResult with multiple outputs"""
        tr = TaskResult(
            outputs=[
                {
                    "name": "text_output",
                    "title": "Text Output",
                    "type": "unicode",
                    "value": "Some text",
                },
                {
                    "name": "file_output",
                    "title": "File Output",
                    "type": "file",
                    "value": "https://toolbox.nextgis.com/api/download/abc123/result.tif",
                }
            ],
            task_id="task-123",
            state="SUCCESS",
        )

        # Test accessing outputs by name
        assert tr["text_output"] == "Some text"
        assert tr["file_output"] == "https://toolbox.nextgis.com/api/download/abc123/result.tif"

        # Test value property raises error for multi-output results
        with pytest.raises(TypeError, match="Value available only for single-output tools"):
            _ = tr.value

    def test_file_path_management(self, tmp_path):
        """Test file path registration and retrieval"""
        tr = TaskResult(
            outputs=[
                {
                    "name": "raster",
                    "title": "Output Raster",
                    "type": "file",
                    "value": "https://toolbox.nextgis.com/api/download/abc123/result.tif",
                },
                {
                    "name": "vector",
                    "title": "Output Vector",
                    "type": "file",
                    "value": "https://toolbox.nextgis.com/api/download/def456/result.geojson",
                }
            ],
            task_id="task-123",
            state="SUCCESS",
        )

        # Create test paths
        raster_path = tmp_path / "result.tif"
        vector_path = tmp_path / "result.geojson"
        raster_path.touch()
        vector_path.touch()

        # Register downloaded files
        tr.register_downloaded_file("raster", raster_path)
        tr.register_downloaded_file("vector", vector_path)

        # Test getting individual file paths
        assert tr.get_file_path("raster") == raster_path
        assert tr.get_file_path("vector") == vector_path
        assert tr.get_file_path("nonexistent") is None

        # Test getting all file paths
        all_paths = tr.get_all_file_paths()
        assert len(all_paths) == 2
        assert all_paths["raster"] == raster_path
        assert all_paths["vector"] == vector_path

        # Test getting serializable file paths
        serializable_paths = tr.get_serializable_file_paths()
        assert len(serializable_paths) == 2
        assert serializable_paths["raster"] == str(raster_path)
        assert serializable_paths["vector"] == str(vector_path)
        assert isinstance(serializable_paths["raster"], str)

    def test_is_file_output(self):
        """Test checking if an output is a file"""
        tr = TaskResult(
            outputs=[
                {
                    "name": "text",
                    "title": "Text Output",
                    "type": "unicode",
                    "value": "Some text",
                },
                {
                    "name": "file",
                    "title": "File Output",
                    "type": "file",
                    "value": "https://toolbox.nextgis.com/api/download/abc123/result.tif",
                }
            ],
            task_id="task-123",
            state="SUCCESS",
        )

        assert tr.is_file_output("file") is True
        assert tr.is_file_output("text") is False
        assert tr.is_file_output("nonexistent") is False

    def test_json_serialization(self, tmp_path):
        """Test that TaskResult can be converted to JSON-compatible format"""
        tr = TaskResult(
            outputs=[
                {
                    "name": "file",
                    "title": "File Output",
                    "type": "file",
                    "value": "https://toolbox.nextgis.com/api/download/abc123/result.tif",
                }
            ],
            task_id="task-123",
            state="SUCCESS",
        )

        # Register a file path
        file_path = tmp_path / "result.tif"
        file_path.touch()
        tr.register_downloaded_file("file", file_path)

        # Convert to dictionary and then to JSON
        result_dict = tr.to_dict()
        json_str = json.dumps(result_dict)
        deserialized = json.loads(json_str)

        # Verify the deserialized data
        assert deserialized["task_id"] == tr.task_id
        assert deserialized["state"] == tr.state
        assert deserialized["outputs"] == tr.outputs
        assert deserialized["file_paths"]["file"] == str(file_path)

        # Ensure we can round-trip through JSON
        assert json.loads(json.dumps(result_dict)) == result_dict
