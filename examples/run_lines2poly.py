from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()

# Enable basic debug logging to stderr
ToolboxClient.configure_logger()

# Initialize client with your API key, use default base url
toolbox = ToolboxClient()

# Use the sample data from https://nextgis.com/data/toolbox/lines2poly/lines2poly_inputs.zip as input download and unzip it

# Run a tool synchronously
lines2poly = toolbox.tool("lines2poly")
result = lines2poly({
    "src_file": toolbox.upload_file("testdata_variousFormats.gpkg")
})

# Download all results into the current directory
toolbox.download_results(result, ".")
print(result.get_all_file_paths())
print(result.get_file_path_as_string("dst_file"))
print(result.get_file_path_as_string("return_lines_file"))
