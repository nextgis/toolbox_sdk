from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()

# Configure logging
ToolboxClient.configure_logger()

# Create the client
toolbox = ToolboxClient()

# Create the tool
generalization = toolbox.tool("generalization")

# Run the tool with the correct parameter
result = generalization(
    {
        "vector": toolbox.upload_file("generalization_input.zip"),
        "threshold": 0.005,
        "look_ahead": 1,
        "iterations": 20,
        "method": "douglas",
    }
)

# Download all results into the current directory
toolbox.download_results(result, ".")

# Check the outputs of the tool
print(result.outputs)  # Get the output definitions with download path and identifier name
print(result.get_all_file_paths())  # Get paths of all resulting files as dict with Path objects
print(result.get_file_path("geometry"))  # Get a specific path of a resulting file named "geometry" as PosixPath
print(result.get_file_path_as_string("geometry"))  # Get a specific path of a resulting file named "geometry" as string
print(result.get_serializable_file_paths())  # Get paths of all resulting files as dict with strings
