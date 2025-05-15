from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()

# Configure logging
ToolboxClient.configure_logger()

# Create the client
toolbox = ToolboxClient()

# Create the tool
qgis2pdf = toolbox.tool("qgis2pdf")

# Run the tool with the correct parameter
result = qgis2pdf(
    {
        "source": toolbox.upload_file("test.zip"),
        "extent": "76.688097,42.945265,77.216935,43.490127",
        "dim_width": 400,
        "dim_height": 500
    }
)

# Download all results into the current directory and list the file path
toolbox.download_results(result, ".")
print(result.get_serializable_file_paths())  # Get paths of all resulting files as dict with strings
