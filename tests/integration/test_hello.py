from toolbox_sdk import ToolboxClient


def test_hello(toolbox_client: ToolboxClient):
    hello = toolbox_client.tool("hello")
    result = hello({"name": "Natalia"})

    expected = "Hello, Natalia!"
    assert result.outputs[0]["value"] == expected
    assert result["hello"] == expected
    assert result.value == expected
