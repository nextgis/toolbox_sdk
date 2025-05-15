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
