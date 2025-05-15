# NextGIS Toolbox SDK

A Python SDK for interacting with NextGIS Toolbox API, providing convenient access to geographical data processing tools.

## Features

- Easy-to-use interface for NextGIS Toolbox tools
- Synchronous and asynchronous task execution
- Robust file upload and download capabilities
- Built-in retry mechanism for API operations
- Progress tracking for file operations
- Comprehensive logging system
- Tool chaining for complex workflows
- Intelligent file name handling from HTTP headers
- Serializable task results for easy storage and sharing

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

# Access the downloaded file path
output_path = result.get_file_path("output")
print(f"Downloaded file: {output_path}")
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

# Get all downloaded file paths
file_paths = result.get_all_file_paths()
for name, path in file_paths.items():
    print(f"{name}: {path}")
```

## Tool Chaining

You can chain tools together by using the output of one tool as the input to another:

```python
from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Load environment variables from .env file
load_dotenv()

# Enable basic debug logging to stderr
ToolboxClient.configure_logger()

# Initialize client with API key from environment variable
toolbox = ToolboxClient()

# Create tool instances
mapcalc = toolbox.tool("r_mapcalc")
ndi = toolbox.tool("ndi")

# Upload the input bands
band4_id = toolbox.upload_file("band4.tif")
band5_id = toolbox.upload_file("band5.tif")

# Process band4 with mapcalc - scale to 0-1 range
band4_result = mapcalc({
    "A": band4_id,
    "expression": "A / 10000",  # Scale NIR band to 0-1 range
})

# Process band5 with mapcalc - scale to 0-1 range
band5_result = mapcalc({
    "A": band5_id,
    "expression": "A / 10000",  # Scale Red band to 0-1 range
})

# Download intermediate results into separate directories, since they have the same file name
toolbox.download_results(band4_result, "band4_result")
toolbox.download_results(band5_result, "band5_result")
# Upload the result
band4_id = toolbox.upload_file(band4_result.get_file_path_as_string("result_raster"))
band5_id = toolbox.upload_file(band5_result.get_file_path_as_string("result_raster"))

# Calculate NDVI using the ndi tool
ndvi_result = ndi({
    "raster_1": band4_id,  # Use output from first tool
    "raster_2": band5_id,  # Use output from second tool
    "formula": "(A-B)/(A+B)"  # NDVI formula
})

# Download the final NDVI result
toolbox.download_results(ndvi_result, "ndvi_output")

# Access specific output path
ndvi_path = ndvi_result.get_file_path_as_string("result_file")
print(f"NDVI raster is available at: {ndvi_path}")
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

### Working with File Paths

The SDK now intelligently handles file names from HTTP headers and provides methods to access downloaded file paths:

```python
# Download results
result = toolbox.download_results(task_result, "output_dir")

# Get path to a specific output file
file_path = result.get_file_path("output_name")
print(f"File path: {file_path}")

# Get path as string (useful for serialization or passing to other libraries)
file_path_str = result.get_file_path_as_string("output_name")
print(f"File path string: {file_path_str}")

# Get all file paths
all_paths = result.get_all_file_paths()
for name, path in all_paths.items():
    print(f"{name}: {path}")

# Get serializable file paths (as strings)
serializable_paths = result.get_serializable_file_paths()
```

### Serializing Task Results

Task results can be serialized to JSON for storage or sharing:

```python
import json

# Get a serializable representation of the result
result_dict = result.to_dict()

# Convert to JSON
json_str = json.dumps(result_dict)

# Save to file
with open("task_result.json", "w") as f:
    f.write(json_str)

# Later, you can load and use the paths
with open("task_result.json", "r") as f:
    loaded_result = json.loads(f.read())
    
print(f"Task ID: {loaded_result['task_id']}")
print(f"File paths: {loaded_result['file_paths']}")
```

## Key Components

- ToolboxClient: Main client for API interaction
- Tool: Represents individual Toolbox tools
- Task: Handles asynchronous operations
- TaskResult: Stores tool outputs and downloaded file paths
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
