"""Shared fixtures for aceteam-nodes tests."""

import pytest
from workflow_engine import WorkflowEngine
from workflow_engine.contexts import InMemoryExecutionContext

# Import node classes so they register on NodeRegistry.DEFAULT at import time.
from aceteam_nodes.nodes.discord import (  # noqa: F401
    DiscordBotInfoNode,
    DiscordListChannelsNode,
    DiscordReadMessagesNode,
    DiscordSendMessageNode,
)
from aceteam_nodes.nodes.shell import ShellNode  # noqa: F401
from aceteam_nodes.nodes.slack import (  # noqa: F401
    SlackListChannelsNode,
    SlackReadMessagesNode,
    SlackSearchMessagesNode,
    SlackSendMessageNode,
)
from aceteam_nodes.nodes.telegram import (  # noqa: F401
    TelegramBotInfoNode,
    TelegramListChatsNode,
    TelegramReadMessagesNode,
    TelegramSendMessageNode,
)
from aceteam_nodes.nodes.xpath_extract import XPathExtractNode  # noqa: F401


@pytest.fixture
def engine() -> WorkflowEngine:
    return WorkflowEngine()


@pytest.fixture
def context() -> InMemoryExecutionContext:
    return InMemoryExecutionContext()
