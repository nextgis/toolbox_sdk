from toolbox_sdk import ToolboxClient


def test_hello(toolbox_client: ToolboxClient):
    hello = toolbox_client.tool("hello")
    result = hello({"name": "Natalia"})

    value = result.outputs[0]["value"]
    assert value.endswith(", Natalia!")
    assert result["result"] == value
    assert result.value == value
