from __future__ import annotations

import logging
import math
import mimetypes
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, BinaryIO, Dict, Optional, Tuple, Union

import filetype
import requests
from requests.adapters import HTTPAdapter
from requests.utils import default_user_agent
from urllib3.util.retry import Retry

from .exceptions import ToolboxAPIError, ToolboxError, ToolboxTimeoutError
from .mime_types import get_extension_from_mime
from .types import ChunkInfo, DownloadConfig, TaskResult
from .version import __version__

logger = logging.getLogger(__name__)


def retry_decorator(
    max_retries: int = 3,
    backoff_factor: float = 0.3,
    retry_on_exceptions: Tuple = (requests.RequestException,),
):
    """Decorator for retrying operations"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except retry_on_exceptions as e:
                    retries += 1
                    if retries == max_retries:
                        raise
                    wait_time = backoff_factor * (2 ** (retries - 1))
                    logger.warning(
                        f"Attempt {retries} failed: {str(e)}. "
                        f"Retrying in {wait_time:.1f} seconds..."
                    )
                    time.sleep(wait_time)
            return None

        return wrapper

    return decorator


class DownloadManager:
    """Manages file downloads with support for parallel processing and progress
    tracking.

    This class handles both simple and parallel downloads with configurable
    chunk sizes, retry logic, and progress callbacks.

    Args:
        client (ToolboxClient): The parent ToolboxClient instance
        config (Optional[DownloadConfig]): Download configuration settings
    """

    def __init__(self, client: ToolboxClient, config: Optional[DownloadConfig] = None):
        self.client = client
        self.config = config or DownloadConfig()

    @retry_decorator(max_retries=3, backoff_factor=0.3)
    def _download_chunk(self, url: str, chunk_info: ChunkInfo) -> Path:
        """Download a single chunk with progress tracking"""
        headers = {"Range": f"bytes={chunk_info.start}-{chunk_info.end}"}
        response = self.client.session.get(url, headers=headers, stream=True)

        response.raise_for_status()
        if response.status_code != 206:
            raise ToolboxError("Range requests not supported")

        with open(chunk_info.temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                if chunk:
                    f.write(chunk)
                    if self.config.progress_callback:
                        self.config.progress_callback(len(chunk))

        return chunk_info.temp_file

    def _get_file_size(self, url: str) -> int:
        """Get total file size using HEAD request"""
        response = self.client.session.head(url)
        response.raise_for_status()
        return int(response.headers.get("content-length", 0))

    def download_file(self, url: str, destination: Union[str, Path]) -> Path:
        """Download a file from the given URL to the specified destination.

        Supports both simple and parallel downloads based on configuration.

        Args:
            url (str): The URL to download from
            destination (Union[str, Path]): Local path where the file should be saved
            headers (Optional[Dict]): Additional HTTP headers for the request

        Returns:
            Path: Path to the downloaded file

        Raises:
            ToolboxError: If download fails after retries
        """
        return (
            self._parallel_download
            if self.config.use_parallel
            else self._simple_download
        )(url, Path(destination))

    def _parallel_download(self, url: str, destination: Path) -> Path:
        """Download file using parallel processing"""
        total_size = self._get_file_size(url)
        chunk_size = math.ceil(total_size / self.config.max_workers)
        chunks = []

        with TemporaryDirectory(dir=destination.parent) as temp_dir_name:
            temp_dir = Path(temp_dir_name)

            # Create chunks with proper boundaries
            for i in range(self.config.max_workers):
                start = i * chunk_size
                end = min((i + 1) * chunk_size - 1, total_size - 1)
                temp_file = temp_dir / f"chunk_{i}.tmp"
                chunks.append(ChunkInfo(start, end, i, temp_file))

            # Download chunks in parallel
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = [
                    executor.submit(self._download_chunk, url, chunk)
                    for chunk in chunks
                ]

                # Wait for all chunks to complete
                completed_files = []
                for future in as_completed(futures):
                    try:
                        completed_files.append(future.result())
                    except Exception as e:
                        raise ToolboxError(f"Chunk download failed: {str(e)}")

            # Combine chunks in order
            with open(destination, "wb") as outfile:
                for chunk in sorted(chunks, key=lambda x: x.index):
                    if chunk.temp_file.exists():
                        with open(chunk.temp_file, "rb") as infile:
                            outfile.write(infile.read())

        return destination

    @retry_decorator(max_retries=3, backoff_factor=0.3)
    def _simple_download(self, url: str, destination: Path) -> Path:
        """Simple streaming download"""
        response = self.client.session.get(url, stream=True)
        response.raise_for_status()

        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                if chunk:
                    f.write(chunk)

        return destination


class Task:
    """Represents an asynchronous task in the NextGIS Toolbox.

    Handles task status checking and result retrieval with support for
    timeout and progress tracking.

    Args:
        client (ToolboxClient): The parent ToolboxClient instance
        task_id (str): Unique identifier of the task
    """

    def __init__(self, client: ToolboxClient, task_id: str):
        self.client = client
        self.task_id = task_id
        self._result: Optional[TaskResult] = None

    @property
    def result(self) -> Optional[TaskResult]:
        return self._result

    @retry_decorator(max_retries=3, backoff_factor=0.3)
    def check_status(self) -> Dict[str, Any]:
        """Check the current status of the task.

        Returns:
            Dict[str, Any]: Task status information including state and progress

        Raises:
            ToolboxAPIError: If API request fails
        """
        response = self.client._get(f"/api/json/status/{self.task_id}/")
        return response.json()

    def wait_for_completion(
        self,
        timeout: int = 600,
        poll_interval: int = 5,
    ) -> TaskResult:
        """Wait for task completion with timeout and status polling.

        Args:
            timeout (int): Maximum time to wait in seconds (default: 600)
            poll_interval (int): Time between status checks in seconds (default: 5)

        Returns:
            TaskResult: Result of the completed task

        Raises:
            ToolboxTimeoutError: If task doesn't complete within timeout
            ToolboxAPIError: If task fails or API request fails
        """
        start_time = time.time()
        last_state = None
        previous_progress = ""

        logger.info(
            f"Waiting for task {self.task_id} to complete (timeout: {timeout}s)"
        )

        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                logger.error(f"Task {self.task_id} timed out after {elapsed_time:.1f}s")
                raise ToolboxTimeoutError(f"Task {self.task_id} timed out")

            status = self.check_status()
            current_state = status["state"]

            # Log state changes
            if current_state != last_state:
                logger.info(f"Task {self.task_id} state: {current_state}")
                last_state = current_state

            # Log progress if available
            if (
                "progress" in status
                and status["progress"] >= 0
                and status["progress"] != previous_progress
            ):
                logger.info(
                    f"Task {self.task_id} progress: {status['progress']}% "
                    f"elapsed time {elapsed_time:.1f}s"
                )
                previous_progress = status["progress"]

            if current_state == "SUCCESS":
                logger.info(
                    f"Task {self.task_id} completed successfully "
                    f"after {elapsed_time:.1f}s"
                )
                self._result = TaskResult(
                    outputs=status["output"],
                    task_id=self.task_id,
                    state=status["state"],
                )
                return self._result

            elif current_state in ("FAILED", "ERROR", "REVOKED"):
                error_msg = status.get("error", "Unknown error")
                logger.error(
                    f"Task {self.task_id} failed after {elapsed_time:.1f}s: {error_msg}"
                )
                raise ToolboxAPIError(f"Task failed: {error_msg}")

            logger.debug(
                f"Task {self.task_id} elapsed time {elapsed_time:.1f}s, "
                f"waiting {poll_interval}s..."
            )
            time.sleep(poll_interval)


class Tool:
    """Represents a NextGIS Toolbox tool that can be executed.

    Provides both synchronous and asynchronous execution methods.

    Args:
        client (ToolboxClient): The parent ToolboxClient instance
        name (str): Name of the tool
    """

    def __init__(self, client: ToolboxClient, name: str):
        self.client = client
        self.name = name

    def __call__(self, inputs: Dict[str, Any]) -> TaskResult:
        """Execute the tool synchronously.

        Args:
            inputs (Dict[str, Any]): Tool parameters and input files

        Returns:
            TaskResult: Result of the tool execution

        Raises:
            ToolboxAPIError: If tool execution fails
        """
        task = self.submit(inputs)
        return task.wait_for_completion()

    @retry_decorator(max_retries=3, backoff_factor=0.3)
    def submit(self, inputs: Dict[str, Any]) -> Task:
        """Submit the tool for asynchronous execution.

        Args:
            inputs (Dict[str, Any]): Tool parameters and input files

        Returns:
            Task: Task object to track execution

        Raises:
            ToolboxAPIError: If submission fails
        """
        json_request = {"operation": self.name, "inputs": inputs, "mode": "ui"}
        response = self.client._post("/api/json/execute/", json=json_request)
        return Task(self.client, response.json()["task_id"])


class ToolboxClient:
    """Client for interacting with the NextGIS Toolbox API.

    Handles authentication, tool execution, file uploads/downloads, and
    result management.

    Args:
        api_key (str): API key
        base_url (str): Base URL of the Toolbox API (default: "https://toolbox.nextgis.com")
        download_config (Optional[DownloadConfig]): Configuration for file downloads
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        download_config: Optional[DownloadConfig] = None,
    ):
        self.base_url = base_url or os.getenv(
            "TOOLBOX_BASE_URL", "https://toolbox.nextgis.com"
        ).rstrip("/")

        api_key = api_key or os.getenv("TOOLBOX_API_KEY")
        if not api_key:
            raise ValueError(
                "API key is required. Provide it via constructor "
                "or TOOLBOX_API_KEY environment variable."
            )

        self.headers = {
            "Authorization": f"Token {api_key}",
            "User-Agent": f"NextGIS-Toolbox-SDK/{__version__} " + default_user_agent(),
        }

        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(self.headers)

        self.download_manager = DownloadManager(self, download_config)

    def tool(self, name: str) -> Tool:
        """Get a tool instance by name.

        Args:
            name (str): Name of the tool to get

        Returns:
            Tool: Tool instance for execution
        """
        return Tool(self, name)

    @retry_decorator(max_retries=3, backoff_factor=0.3)
    def upload_file(self, file: Union[str, Path, BinaryIO]) -> str:
        """Upload a file to the Toolbox.

        Args:
            file (Union[str, Path, BinaryIO]): File to upload, can be path
                or file object

        Returns:
            str: File ID for use in tool parameters

        Raises:
            ToolboxAPIError: If upload fails
        """
        if isinstance(file, (str, Path)):
            path = Path(file)
            with open(path, "rb") as f:
                return self._upload_file_obj(f, path.name)
        return self._upload_file_obj(file, getattr(file, "name", "unnamed"))

    def download_file(
        self,
        file_id: str,
        destination: Union[str, Path],
        use_parallel: Optional[bool] = None,
    ) -> Path:
        """Download a file from the Toolbox.

        Args:
            file_id (str): ID or URL of file to download
            destination (Union[str, Path]): Where to save the file
            use_parallel (Optional[bool]): Override parallel download setting

        Returns:
            Path: Path to downloaded file

        Raises:
            ToolboxError: If download fails
        """
        if use_parallel is not None:
            original_parallel = self.download_manager.config.use_parallel
            self.download_manager.config.use_parallel = use_parallel

        try:
            url = (
                file_id
                if file_id.startswith(("http://", "https://"))
                else f"{self.base_url}/api/download/{file_id}"
            )

            # Get file size
            response = self.session.head(url)
            total_size = int(response.headers.get("content-length", 0))

            logger.info(
                f"Starting download to {destination} "
                f"({total_size / 1024 / 1024:.1f} MB)"
            )

            if use_parallel:
                logger.info("Using parallel download")

            downloaded = 0
            last_percentage = 0

            def progress_callback(chunk_size):
                nonlocal downloaded, last_percentage
                downloaded += chunk_size
                percentage = int((downloaded / total_size) * 100)
                if percentage > last_percentage and percentage % 10 == 0:
                    logger.info(f"Download progress: {percentage}%")
                    last_percentage = percentage

            # Add progress callback to download manager config
            self.download_manager.config.progress_callback = progress_callback

            result = self.download_manager.download_file(url, destination)
            logger.info(f"Download completed to {destination}")
            return result

        finally:
            if use_parallel is not None:
                self.download_manager.config.use_parallel = original_parallel

    def download_results(
        self,
        result: TaskResult,
        output_dir: Union[str, Path] = ".",
    ) -> Dict[str, Path]:
        """Download all file outputs from a task result.

        Args:
            result (TaskResult): Task result containing outputs
            output_dir (Union[str, Path]): Directory to save files to
                (default: current directory)

        Returns:
            Dict[str, Path]: Mapping of output names to downloaded file paths

        Raises:
            ToolboxError: If any download fails
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files = {}

        for output in result.outputs:
            if output.get("type") == "file":
                file_name = output.get("name", "unnamed")
                base_name = Path(file_name).stem

                counter = 1
                while True:
                    if counter == 1:
                        unique_name = base_name
                    else:
                        unique_name = f"{base_name}_{counter}"

                    file_path = output_dir / unique_name
                    if not file_path.exists():
                        break
                    counter += 1

                downloaded_path = self.download_file(output["value"], file_path)
                downloaded_files[file_name] = downloaded_path
                logger.info(f"Downloaded {file_name} to {downloaded_path}")

        file_types = self.determine_file_types(downloaded_files)
        renamed_files = self.rename_files_with_extensions(downloaded_files, file_types)

        return renamed_files

    def determine_file_types(self, files: Dict[str, Path]) -> Dict[Path, str]:
        """Determine the MIME types of the downloaded files.

        Args:
            files (Dict[str, Path]): A dictionary mapping original file names
                to their downloaded paths.

        Returns:
            Dict[Path, str]: A dictionary mapping file paths to their
                determined MIME types.
        """
        file_types = {}
        for file_path in files.values():
            # Try to guess the type using mimetypes
            mime_type, _ = mimetypes.guess_type(str(file_path))

            # If mimetypes couldn't determine the type, use filetype
            if mime_type is None:
                kind = filetype.guess(str(file_path))
                mime_type = (
                    kind.mime if kind is not None else "application/octet-stream"
                )

            file_types[file_path] = mime_type
        return file_types

    def rename_files_with_extensions(
        self,
        files: Dict[str, Path],
        file_types: Dict[Path, str],
    ) -> Dict[str, Path]:
        """Rename the downloaded files with appropriate file extensions based
        on their MIME types.

        Args:
            files (Dict[str, Path]): A dictionary mapping original file names
                to their downloaded paths.
            file_types (Dict[Path, str]): A dictionary mapping file paths
                to their MIME types.

        Returns:
            Dict[str, Path]: A dictionary mapping original file names to their
                new paths with correct extensions.
        """
        renamed_files = {}
        for original_name, file_path in files.items():
            mime_type = file_types[file_path]
            extension = self._get_extension_from_mime(mime_type)
            new_path = file_path.with_suffix(extension)
            file_path.rename(new_path)
            renamed_files[original_name] = new_path
            logger.info(f"Renamed {file_path} to {new_path}")
        return renamed_files

    @staticmethod
    def configure_logger(level: logging._Level = logging.DEBUG):
        """Configure basic logging for debugging or testing purposes"""
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(level)

    def _get_extension_from_mime(self, mime_type: str) -> str:
        return get_extension_from_mime(mime_type)

    def _upload_file_obj(self, file_obj: BinaryIO, filename: str) -> str:
        """Internal file upload helper with progress tracking"""
        # Get file size
        file_obj.seek(0, 2)  # Seek to end
        file_size = file_obj.tell()
        file_obj.seek(0)  # Reset to beginning

        logger.info(f"Starting upload of {filename} ({file_size / 1024 / 1024:.1f} MB)")

        # Create upload progress tracker
        uploaded = 0
        last_percentage = 0

        def upload_callback(monitor):
            nonlocal uploaded, last_percentage
            uploaded += len(monitor)
            percentage = int((uploaded / file_size) * 100)
            if percentage > last_percentage and percentage % 10 == 0:
                logger.info(f"Upload progress for {filename}: {percentage}%")
                last_percentage = percentage

        # Create generator that tracks progress
        def file_generator():
            chunk_size = 8192
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                upload_callback(chunk)
                yield chunk

        response = self._post(
            f"/api/upload/?filename={filename}", data=file_generator()
        )
        logger.info(f"Upload completed for {filename}")
        return response.text

    def _get(self, path: str, **kwargs) -> requests.Response:
        """Make GET request"""
        response = self.session.get(f"{self.base_url}{path}", **kwargs)
        response.raise_for_status()
        return response

    def _post(self, path: str, **kwargs) -> requests.Response:
        """Make POST request"""
        response = self.session.post(f"{self.base_url}{path}", **kwargs)
        response.raise_for_status()
        return response
