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
            return TypeError("Value available only for single-output tools")
        return self.outputs[0]["value"]


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
