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

# Create the mapcalc tool for processing, this will be reused three times
r_mapcalc = toolbox.tool("r_mapcalc")

# Upload the two raster files
A_upload = toolbox.upload_file("band4.tif")
B_upload  = toolbox.upload_file("band5.tif")

# Run r_mapcalc to add the two raster, use the upload ids
result_a = r_mapcalc(
    {
        "A": A_upload ,
        "B": B_upload ,
        "expression": "A + B",
    }
)

# Run r_mapcalc to subtract the two raster, use the upload ids
result_b = r_mapcalc(
    {
        "A": A_upload ,
        "B": B_upload ,
        "expression": "A - B",
    }
)

# Run r_mapcalc to multiply the two raster results from the previous computation
# The value property of the result will always use the first file output
result_c = r_mapcalc(
    {
        "A": result_a.value,
        "B": result_b.value,
        "expression": "A * B",
    }
)

# Download all results into the current directory
toolbox.download_results(result_c, ".")

# Check the outputs of the last process
print(result_c.value)
print(result_c.outputs)
print(result_c.outputs[0]["value"])
print(result_c.get_all_file_paths())
print(result_c.get_file_path_as_string("result_raster"))
