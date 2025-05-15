from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()

# Enable basic debug logging to stderr
ToolboxClient.configure_logger()

# Create the client
toolbox = ToolboxClient()

# Create the tool
r_mapcalc = toolbox.tool("r_mapcalc")

# Run the tool with the correct parameter
task = r_mapcalc.submit(
    {
        "A": toolbox.upload_file("band4.tif"),
        "B": toolbox.upload_file("band5.tif"),
        "expression": "A + B",
    }
)

# Run the task with 120s timeout
result = task.wait_for_completion(timeout=120)

# Download all results into the current directory
toolbox.download_results(result, ".")

# Check the outputs of the tool
print(result.outputs)
print(result.get_all_file_paths())
