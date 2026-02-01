"""
Zero Me - Tools Module
Tool implementations for agents
"""

from tools.notion_tools import (
    create_notion_page,
    read_notion_page,
    search_notion,
    add_todo,
    get_todos,
    update_todo,
    add_calendar_event,
    get_calendar_events,
    update_calendar_event,
    delete_calendar_event,
)
from tools.email_tools import send_email, draft_email
from tools.memory_tools import store_memory, retrieve_memory, search_memory
from tools.analytics_tools import log_metric, log_question_count, log_parameter_change

__all__ = [
    # Notion tools
    "create_notion_page",
    "read_notion_page",
    "search_notion",
    "add_todo",
    "get_todos",
    "update_todo",
    "add_calendar_event",
    "get_calendar_events",
    "update_calendar_event",
    "delete_calendar_event",
    # Email tools
    "send_email",
    "draft_email",
    # Memory tools
    "store_memory",
    "retrieve_memory",
    "search_memory",
    # Analytics tools
    "log_metric",
    "log_question_count",
    "log_parameter_change",
]
