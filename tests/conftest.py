from os import environ

import pytest
from dotenv import load_dotenv

from toolbox_sdk import ToolboxClient


@pytest.fixture(scope="session", autouse=True)
def configure_logger():
    ToolboxClient.configure_logger()


@pytest.fixture(scope="session")
def toolbox_client():
    load_dotenv()

    if "TOOLBOX_API_KEY" not in environ:
        pytest.skip("TOOLBOX_API_KEY environment variable not set")

    return ToolboxClient()
