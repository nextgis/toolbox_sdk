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
        "method": "douglas",
    }
)

# Download all results into the current directory
toolbox.download_results(result, ".")

# Check the outputs of the tool
print(result.outputs)
