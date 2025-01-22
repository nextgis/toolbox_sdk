# NextGIS Toolbox SDK

A Python SDK for interacting with NextGIS Toolbox API, providing convenient access to geographical data processing tools.

## Features

- Easy-to-use interface for NextGIS Toolbox tools
- Synchronous and asynchronous task execution
- Robust file upload and download capabilities
- Built-in retry mechanism for API operations
- Progress tracking for file operations
- Comprehensive logging system

## Installation

```bash
pip install toolbox-sdk
```

## Quickstart

Run the hello tool and use the `result.value` property to get the result of the run:

```python
from toolbox_sdk import ToolboxClient

# Initialize client with your API key, use default base url
toolbox = ToolboxClient("your-api-key")

# Create the tool
hello = toolbox.tool("hello")

# Run the tool with the correct parameter
result = hello({"name": "Natalia"})

# Print the result
print(result.value)
```

Running convert operation and configure the logger to watch the progress:

```python
from toolbox_sdk import ToolboxClient

# Enable basic debug logging to stderr
ToolboxClient.configure_logger()

# Initialize client with your API key, use default base url
toolbox = ToolboxClient("your-api-key")

# Run a tool synchronously
convert = toolbox.tool("convert")
result = convert({
    "source": toolbox.upload_file("input.geojson"),
    "format": "GPKG"
})

# Download the resulting file into the current directory
toolbox.download_results(result, ".")
```

Running generalization operation:

```python
from toolbox_sdk import ToolboxClient

# Create the client with API key and on premise Toolbox URL
toolbox = ToolboxClient(
    api_key="your-api-key",
    base_url="https://toolbox.example.com",
)

# Create the tool
generalization = toolbox.tool("generalization")

# Run the tool with the correct parameter
result = generalization({
    "vector": toolbox.upload_file("generalization_input.zip"),
    "threshold": 0.005,
    "method": "douglas"
})

# Download all results into the current directory
toolbox.download_results(result, ".")
```

## Environment Variables

`ToolboxClient` uses the `TOOLBOX_API_KEY` and `TOOLBOX_BASE_URL` environment variables as default values for the corresponding parameters. Thus, you can configure it using these variables.

```
$ export TOOLBOX_API_KEY=your-api-key
$ python
>>> from toolbox_sdk import ToolboxClient
>>> toolbox = ToolboxClient()
```

This also means that you can use `.env` files to configure the SDK via the [dotenv](https://github.com/theskumar/python-dotenv) library:

```
$ unset TOOLBOX_API_KEY
$ echo TOOLBOX_API_KEY=your-api-key > .env
$ pip install python-dotenv
$ python
>>> from dotenv import load_env
>>> load_env()
>>>
>>> from toolbox_sdk import ToolboxClient
>>> toolbox = ToolboxClient()
```

## Advanced Usage

### Asynchronous Operations

The `.env` file must be present that contains the API key:

```
TOOLBOX_API_KEY=your-api-key
```

```python
from dotenv import load_dotenv
from toolbox_sdk import ToolboxClient

# Get the API key from the .env file
load_dotenv()

# Configure logger and create the client
ToolboxClient.configure_logger()
toolbox = ToolboxClient()

# Create the tool
mapcalc = toolbox.tool("r_mapcalc")

# Set the correct parameter
task = mapcalc.submit({
    "A": toolbox.upload_file("band4.tif"),
    "B": toolbox.upload_file("band5.tif"),
    "expression": "A + B"
})

# Run the task
result = task.wait_for_completion(timeout=120)

# Download all results into the current directory
toolbox.download_results(result, ".")

# Check the outputs of the tool
print(result.outputs)
```

## Key Components

- ToolboxClient: Main client for API interaction
- Tool: Represents individual Toolbox tools
- Task: Handles asynchronous operations
- DownloadManager: Manages file downloads

## Error Handling

The SDK provides specific exceptions:

- ToolboxError: Base exception
- ToolboxAPIError: API-related errors
- ToolboxTimeoutError: Timeout errors

### Requirements

- Python ≥ 3.8
- requests ≥ 2.28.0
- filetype >= 1.2.0
- pytest ≥ 8.3.4 (for testing)
- responses ≥ 0.25.3 (for testing)
- python-dotenv ≥ 1.0.1 (for examples)

## License

MIT License

## Support

For issues and feature requests, please use the GitHub issue tracker.

## Development

First, install [hatch](https://hatch.pypa.io/), then clone the repository:

```bash
$ git clone git@github.com:nextgis/toolbox_sdk.git
$ cd toolbox_sdk
```

And then use hatch commands: `hatch test`, `hatch fmt`, `hatch build`, etc. To run integration tests, provide `TOOLBOX_API_KEY` (and optionally `TOOLBOX_BASE_URL`) in the `.env` file to avoid setting them using environment variables each time. The tests will use `load_env()` as described above.
