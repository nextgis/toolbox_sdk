import os

from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()
token = os.getenv("TOOLBOX_API_KEY")
base_url = os.getenv("TOOLBOX_BASE_URL", default="https://toolbox.nextgis.com")

# Configure logging
ToolboxClient.configure_logger()

# Create the client
toolbox = ToolboxClient(api_key=token, base_url=base_url)

# Create the tool
r_mapcalc = toolbox.tool("r_mapcalc")

# Run the tool with the correct parameter
result = r_mapcalc(
    {
        "A": toolbox.upload_file("band4.tif"),
        "B": toolbox.upload_file("band5.tif"),
        "expression": "A + B",
    }
)

# Download all results into the current directory
toolbox.download_results(result, ".")

# Check the outputs of the tool
print(result.outputs)
print(result.get_all_file_paths())
print(result.get_file_path_as_string("result_raster"))
