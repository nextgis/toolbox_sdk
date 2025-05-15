from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TaskResult:
    """Represents a completed task result

    The outputs have the following format:
    [{'name': 'result_raster',
      'title': 'Result raster file',
      'type': 'file',
      'value': 'https://toolbox.nextgis.com/api/download/a3eafc99-cf5d-4bd0-a42e-e1242bfb52ae/result_raster'}]
    """

    outputs: List[Dict[str, Any]]
    task_id: str
    state: str
    _downloaded_files: Dict[str, Path] = None

    def __post_init__(self):
        """Initialize the downloaded files dictionary"""
        self._downloaded_files = {}

    def __getitem__(self, name: str) -> Any:
        """Get the output value by its name"""
        for o in self.outputs:
            if o["name"] == name:
                return o["value"]
        else:
            raise KeyError(f"Output '{name}' not found")

    @property
    def value(self):
        """Get the output value for single-output tools"""
        if len(self.outputs) != 1:
            raise TypeError("Value available only for single-output tools")
        return self.outputs[0]["value"]

    def get_file_path(self, name: str) -> Optional[Path]:
        """Get the local file path for a downloaded output file

        Args:
            name (str): The name of the output

        Returns:
            Optional[Path]: The path to the downloaded file or None if not downloaded
        """
        return self._downloaded_files.get(name)

    def get_file_path_as_string(self, name: str) -> Optional[str]:
        """Get the local file path for a downloaded output file as string

        Args:
            name (str): The name of the output

        Returns:
            Optional[str]: The path as string to the downloaded file or None if not downloaded
        """
        if self._downloaded_files.get(name):
            return str(self._downloaded_files.get(name))
        return None

    def get_all_file_paths(self) -> Dict[str, Path]:
        """Get all downloaded file paths

        Returns:
            Dict[str, Path]: Dictionary mapping output names to file paths
        """
        return self._downloaded_files.copy()

    def get_serializable_file_paths(self) -> Dict[str, str]:
        """Get all downloaded file paths as serializable strings

        Returns:
            Dict[str, str]: Dictionary mapping output names to file path strings
        """
        return {k: str(v) for k, v in self._downloaded_files.items()}

    def register_downloaded_file(self, name: str, path: Path):
        """Register a downloaded file

        Args:
            name (str): The name of the output
            path (Path): The path to the downloaded file
        """
        self._downloaded_files[name] = path

    def is_file_output(self, name: str) -> bool:
        """Check if an output is a file

        Args:
            name (str): The name of the output

        Returns:
            bool: True if the output is a file, False otherwise
        """
        for o in self.outputs:
            if o["name"] == name:
                return o.get("type") == "file"
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert the TaskResult to a serializable dictionary

        Returns:
            Dict[str, Any]: A dictionary representation of the TaskResult
        """
        return {
            "outputs": self.outputs,
            "task_id": self.task_id,
            "state": self.state,
            "file_paths": self.get_serializable_file_paths()
        }


@dataclass
class DownloadConfig:
    """Configuration for file downloads"""

    chunk_size: int = 8192
    max_workers: int = 4
    use_parallel: bool = True
    verify_hash: bool = True
    max_retries: int = 3
    backoff_factor: float = 0.3
    progress_callback: Optional[Callable[[int], None]] = None


@dataclass
class ChunkInfo:
    """Information about a file chunk for parallel download"""

    start: int
    end: int
    index: int
    temp_file: Path
