from __future__ import annotations


class ToolboxError(Exception):
    """Base exception for Toolbox SDK errors"""


class ToolboxAPIError(ToolboxError):
    """API-related errors"""


class ToolboxTimeoutError(ToolboxError):
    """Timeout errors"""
