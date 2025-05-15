from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()

# Enable basic debug logging to stderr
ToolboxClient.configure_logger()

# Initialize client with your API key, use default base url
toolbox = ToolboxClient()

# Run a tool synchronously
kmldae2footprints = toolbox.tool("kmldae2footprints")

# Download the sample data here https://nextgis.com/data/toolbox/kml2geodata/kml2geodata_inputs.zip and unzip it
result = kmldae2footprints({
    "zip_with_kmls": toolbox.upload_file("sample.zip")
})

# Download all results into the current directory
toolbox.download_results(result, ".")
print(result.get_all_file_paths())
