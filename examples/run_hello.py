from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient

# Get the access token from the environment file .env
load_dotenv()

# Create the client
toolbox = ToolboxClient()

# Create the tool
hello = toolbox.tool("hello")

# Run the tool with the correct parameter
result = hello({"name": "Natalia"})

# Print the result
print(result["hello"])
# Value is directly accessible
print(result.value)
