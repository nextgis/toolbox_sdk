# This example chains two qgis intersect algorithms
from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()

# Enable basic debug logging to stderr
ToolboxClient.configure_logger()

# Initialize client with your API key, use default base url
toolbox = ToolboxClient()

# Create the intersect tool
qgis_intersect = toolbox.tool("qgis_intersect")

# Use the sample data from https://nextgis.com/data/toolbox/lines2poly/lines2poly_inputs.zip as input download and unzip it

lines = toolbox.upload_file("lines.gpkg")
polygons = toolbox.upload_file("polygons.gpkg")
print(lines, polygons)

# Run intersect using the upload links
first_result = qgis_intersect({
    "input": lines,
    "overlay": polygons,
    "input_fields": "",
    "overlay_fields": "",
    "overlay_fields_prefix": ""
})

# Use the intersection value of the first run as input for the second run
second_result = qgis_intersect({
    "input": first_result.value,
    "overlay": polygons,
    "input_fields": "",
    "overlay_fields": "",
    "overlay_fields_prefix": ""
})


# Download the final results into the current directory
toolbox.download_results(second_result, ".")
print(second_result.get_all_file_paths())
