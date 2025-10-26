from __future__ import annotations

import logging
import os
import re
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Tuple, Union
from urllib.parse import unquote

import requests
from requests import JSONDecodeError
from requests.adapters import HTTPAdapter
from requests.utils import default_user_agent
from urllib3.util.retry import Retry

from .exceptions import ToolboxAPIError, ToolboxTimeoutError
from .types import DownloadConfig, TaskResult
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
        response = self.client._get(f"/api/tasks/{self.task_id}")
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

        logger.info(f"Waiting for task {self.task_id} to complete (timeout: {timeout}s)")

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
                    f"Task {self.task_id} completed successfully after {elapsed_time:.1f}s"
                )
                self._result = TaskResult(
                    outputs=status["output"],
                    task_id=self.task_id,
                    state=status["state"],
                )
                return self._result

            elif current_state in ("FAILED", "ERROR", "REVOKED", "CANCELLED"):
                error_msg = status.get("error", "Unknown error")
                logger.error(f"Task {self.task_id} failed after {elapsed_time:.1f}s: {error_msg}")
                raise ToolboxAPIError(
                    f"Task failed: state: {current_state} error message: {error_msg}"
                )

            logger.debug(
                f"Task {self.task_id} elapsed time {elapsed_time:.1f}s, "
                f"waiting {poll_interval}s..."
            )
            time.sleep(poll_interval)


class Tool:
    """Represents a Toolbox tool"""

    def __init__(self, client, name):
        self.client = client
        self.name = name

    def submit(self, inputs: Dict[str, Any]) -> Task:
        """Submit a task to run the tool asynchronously.

        Args:
            inputs (Dict[str, Any]): Tool inputs

        Returns:
            Task: Task object to track execution
        """
        # Process inputs to handle TaskResult objects
        processed_inputs = {}
        for key, value in inputs.items():
            if isinstance(value, TaskResult):
                # If the input is a single-output TaskResult, use its value
                if len(value.outputs) == 1:
                    processed_inputs[key] = value.value
                else:
                    # For multi-output TaskResult, check if the key exists
                    try:
                        processed_inputs[key] = value[key]
                    except KeyError:
                        raise ValueError(
                            "Cannot use multi-output TaskResult directly as input. "
                            "Please specify which output to use with result['output_name']"
                        )
            else:
                processed_inputs[key] = value

        # Construct the correct JSON payload
        payload = {"operation": self.name, "inputs": processed_inputs}

        logger.debug(f"Submitting task for tool {self.name} with payload: {payload}")

        response = self.client.session.post(
            f"{self.client.base_url}/api/tasks/",
            json=payload,
        )

        # If there's an error, try to get more details from the response
        if response.status_code >= 400:
            try:
                error_details = response.json()
                error_message = f"API error: {response.status_code} - {error_details}"
            except JSONDecodeError as e:
                error_message = (
                    f"API error: {response.status_code} - {response.text} error: {str(e)}"
                )
            logger.error(error_message)
            raise ToolboxAPIError(error_message)

        response.raise_for_status()
        data = response.json()
        return Task(self.client, data["task_id"])

    def __call__(self, inputs: Dict[str, Any]) -> TaskResult:
        """Run the tool synchronously.

        Args:
            inputs (Dict[str, Any]): Tool inputs

        Returns:
            TaskResult: Tool execution result
        """
        task = self.submit(inputs)
        return task.wait_for_completion()


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
        retry_strategy = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(self.headers)

        self.download_config = download_config or DownloadConfig()

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

    @retry_decorator(max_retries=3, backoff_factor=0.3)
    def download_file(
        self,
        file_id: str,
        destination: Union[str, Path],
        output_name: Optional[str] = None,
        task_result: Optional[TaskResult] = None,
    ) -> Path:
        """Download a file from the Toolbox.

        Args:
            file_id (str): ID or URL of file to download
            destination (Union[str, Path]): Where to save the file
            output_name (Optional[str]): Name of the output this file belongs to
            task_result (Optional[TaskResult]): Task result to register the file with

        Returns:
            Path: Path to downloaded file

        Raises:
            ToolboxError: If download fails
        """
        url = (
            file_id
            if file_id.startswith(("http://", "https://"))
            else f"{self.base_url}/api/download/{file_id}"
        )

        # Get file size and check for content-disposition header
        response = self.session.head(url)
        total_size = int(response.headers.get("content-length", 0))

        # Try to get filename from content-disposition header
        content_disposition = response.headers.get("content-disposition")
        filename = None
        if content_disposition:
            filename_match = re.search(r'filename="([^"]+)"|filename=([^;]+)', content_disposition)
            if filename_match:
                filename = unquote(filename_match.group(1) or filename_match.group(2))

        # Determine destination path
        destination_path = Path(destination)
        if destination_path.exists() and destination_path.is_dir():
            # If destination is a directory, use the filename from content-disposition or a default
            if filename:
                destination_path = destination_path / filename
        elif filename and not destination_path.suffix:
            # If destination doesn't have an extension but looks like a directory path,
            # treat it as a directory and append the filename
            try:
                # Check if parent directory exists or can be created
                parent = destination_path.parent
                if not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
                if not destination_path.exists() or destination_path.is_dir():
                    destination_path = destination_path / filename
            except (OSError, NotADirectoryError):
                # If we can't create/access the directory, treat destination as a file path
                pass

        # Ensure parent directory exists
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Starting download to {destination_path} ({total_size / 1024 / 1024:.1f} MB)"
        )

        # Simple streaming download
        response = self.session.get(url, stream=True)
        response.raise_for_status()

        downloaded = 0
        last_percentage = 0

        with open(destination_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=self.download_config.chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percentage = int((downloaded / total_size) * 100)
                    if percentage > last_percentage and percentage % 10 == 0:
                        logger.info(f"Download progress: {percentage}%")
                        last_percentage = percentage

        logger.info(f"Download completed to {destination_path}")

        # Register the downloaded file with the task result if provided
        if task_result is not None and output_name is not None:
            task_result.register_downloaded_file(output_name, destination_path)

        return destination_path

    def download_results(
        self,
        task_result: TaskResult,
        destination: Union[str, Path],
    ) -> TaskResult:
        """Download all file outputs from a task result.

        Args:
            task_result (TaskResult): The task result containing outputs
            destination (Union[str, Path]): Directory where to save the files

        Returns:
            TaskResult: The same task result with registered file paths
        """
        destination = Path(destination)
        if not destination.exists():
            destination.mkdir(parents=True)

        for output in task_result.outputs:
            if output.get("type") == "file":
                file_id = output["value"]
                self.download_file(
                    file_id=file_id,
                    destination=destination,
                    output_name=output["name"],
                    task_result=task_result,
                )

        return task_result

    @staticmethod
    def configure_logger(level: logging._Level = logging.DEBUG):
        """Configure basic logging for debugging or testing purposes"""
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(level)

    def _upload_file_obj(self, file_obj: BinaryIO, filename: str) -> str:
        """Internal file upload helper with progress tracking"""
        response = self._post(
            f"/api/upload/?filename={filename}",
            data=FileUploadMonitor(file_obj, filename),
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


class FileUploadMonitor:
    def __init__(self, fileobj: BinaryIO, name: str):
        self.fileobj = fileobj

        fileobj.seek(0, 2)  # Seek to end
        self.file_size = fileobj.tell()
        fileobj.seek(0)  # Reset to beginning

        self.uploaded = 0
        self.last_percentage = 0

        logger.info(f"Starting upload of {name} ({self.file_size} bytes)")

    def __len__(self):
        # NOTE: We need to report the length of the file, otherwise requests
        # will switch to chunked transfer encoding and it may fail.
        return self.file_size

    def __iter__(self):
        chunk_size = 8192
        while True:
            chunk = self.fileobj.read(chunk_size)
            if not chunk:
                break
            yield chunk
            self.upload_callback(len(chunk))

    def upload_callback(self, nbytes: int):
        self.uploaded += nbytes
        percentage = int((self.uploaded / self.file_size) * 100)
        if percentage > self.last_percentage and percentage % 10 == 0:
            logger.info(f"Upload progress: {percentage}%")
            self.last_percentage = percentage
