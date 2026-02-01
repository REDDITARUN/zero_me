"""
Zero Me - Notion Tools
Tools for Doc, Todo, and Calendar operations using Notion API
"""

import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
from langchain.tools import tool
from loguru import logger
import httpx

# Import colorful logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logging_utils import log_tool_call, log_tool_result

try:
    from notion_client import Client as NotionClient
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    logger.warning("notion-client not installed. Notion tools will be disabled.")


NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def get_notion_client() -> Optional[NotionClient]:
    """Get Notion client instance."""
    if not NOTION_AVAILABLE:
        return None
    
    token = os.getenv("NOTION_TOKEN")
    if not token:
        logger.warning("NOTION_TOKEN not found")
        return None
    
    return NotionClient(auth=token)


def query_notion_database(database_id: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Query a Notion database using direct HTTP call.
    The notion-client library's request method has issues, so we use httpx directly.
    """
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN not found")
    
    response = httpx.post(
        f"{NOTION_API_URL}/databases/{database_id}/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        json=body or {},
        timeout=30.0,
    )
    
    if response.status_code != 200:
        raise Exception(f"Notion API error: {response.status_code} - {response.text}")
    
    return response.json()


# ============================================
# DOCUMENT TOOLS
# ============================================

@tool
def create_notion_page(
    title: str,
    content: str,
    parent_page_id: Optional[str] = None,
) -> str:
    """
    Create a new page/document in Notion.
    
    Args:
        title: The title of the page
        content: The content to add to the page (plain text)
        parent_page_id: Optional parent page ID. If not provided, uses NOTION_DOC_PARENT from env.
    
    Returns:
        Success message with page ID or error message
    """
    log_tool_call("create_notion_page", {"title": title})
    client = get_notion_client()
    if not client:
        result = "Error: Notion is not configured. Please set NOTION_TOKEN."
        log_tool_result("create_notion_page", result, success=False)
        return result
    
    try:
        # Build parent reference - use env variable as default
        actual_parent_id = parent_page_id or os.getenv("NOTION_DOC_PARENT")
        if not actual_parent_id:
            result = "Error: No parent page ID provided and NOTION_DOC_PARENT not set in environment."
            log_tool_result("create_notion_page", result, success=False)
            return result
        
        parent = {"page_id": actual_parent_id}
        
        # Create the page
        new_page = client.pages.create(
            parent=parent,
            properties={
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]
        )
        
        page_id = new_page["id"]
        result = f"Successfully created document '{title}'. Page ID: {page_id}"
        log_tool_result("create_notion_page", result, success=True)
        return result
        
    except Exception as e:
        result = f"Error creating document: {str(e)}"
        log_tool_result("create_notion_page", result, success=False)
        return result


@tool
def read_notion_page(page_id: str) -> str:
    """
    Read the content of a Notion page.
    
    Args:
        page_id: The Notion page ID to read
    
    Returns:
        The page content or error message
    """
    log_tool_call("read_notion_page", {"page_id": page_id})
    client = get_notion_client()
    if not client:
        result = "Error: Notion is not configured. Please set NOTION_TOKEN."
        log_tool_result("read_notion_page", result, success=False)
        return result
    
    try:
        # Get page metadata
        page = client.pages.retrieve(page_id=page_id)
        
        # Get page title
        title = "Untitled"
        if "properties" in page:
            for prop in page["properties"].values():
                if prop.get("type") == "title" and prop.get("title"):
                    title = prop["title"][0]["plain_text"] if prop["title"] else "Untitled"
                    break
        
        # Get page content (blocks)
        blocks = client.blocks.children.list(block_id=page_id)
        
        content_parts = [f"# {title}\n"]
        for block in blocks.get("results", []):
            block_type = block.get("type")
            if block_type == "paragraph":
                text = block.get("paragraph", {}).get("rich_text", [])
                content_parts.append("".join([t.get("plain_text", "") for t in text]))
            elif block_type == "heading_1":
                text = block.get("heading_1", {}).get("rich_text", [])
                content_parts.append(f"# {''.join([t.get('plain_text', '') for t in text])}")
            elif block_type == "heading_2":
                text = block.get("heading_2", {}).get("rich_text", [])
                content_parts.append(f"## {''.join([t.get('plain_text', '') for t in text])}")
            elif block_type == "bulleted_list_item":
                text = block.get("bulleted_list_item", {}).get("rich_text", [])
                content_parts.append(f"• {''.join([t.get('plain_text', '') for t in text])}")
        
        return "\n\n".join(content_parts)
        
    except Exception as e:
        logger.error(f"Failed to read Notion page: {e}")
        return f"Error reading document: {str(e)}"


@tool
def search_notion(query: str, filter_type: str = "page") -> str:
    """
    Search for pages in Notion.
    
    Args:
        query: Search query
        filter_type: Type to filter by - "page" or "database"
    
    Returns:
        List of matching pages or error message
    """
    log_tool_call("search_notion", {"query": query, "filter_type": filter_type})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    try:
        results = client.search(
            query=query,
            filter={"property": "object", "value": filter_type}
        )
        
        if not results.get("results"):
            return f"No {filter_type}s found matching '{query}'"
        
        items = []
        for item in results["results"][:10]:  # Limit to 10
            title = "Untitled"
            if "properties" in item:
                for prop in item["properties"].values():
                    if prop.get("type") == "title" and prop.get("title"):
                        title = prop["title"][0]["plain_text"] if prop["title"] else "Untitled"
                        break
            items.append(f"- {title} (ID: {item['id']})")
        
        return f"Found {len(items)} {filter_type}(s):\n" + "\n".join(items)
        
    except Exception as e:
        logger.error(f"Failed to search Notion: {e}")
        return f"Error searching: {str(e)}"


# ============================================
# TODO TOOLS
# ============================================

@tool
def add_todo(
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
    database_id: Optional[str] = None,
) -> str:
    """
    Add a new todo item to Notion.
    
    Args:
        title: The todo title/task name
        description: Optional description
        due_date: Optional due date in YYYY-MM-DD format
        database_id: Notion database ID for todos. If not provided, uses NOTION_TODO_DB env var.
    
    Returns:
        Success message or error
    """
    log_tool_call("add_todo", {"title": title, "due_date": due_date or "none"})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    db_id = database_id or os.getenv("NOTION_TODO_DB")
    if not db_id:
        return "Error: No todo database configured. Please set NOTION_TODO_DB environment variable."
    
    try:
        properties = {
            "Name": {
                "title": [{"text": {"content": title}}]
            },
            "Status": {
                "select": {"name": "Not started"}
            },
        }
        
        if description:
            properties["Description"] = {
                "rich_text": [{"text": {"content": description}}]
            }
        
        if due_date:
            properties["Due Date"] = {
                "date": {"start": due_date}
            }
        
        new_page = client.pages.create(
            parent={"database_id": db_id},
            properties=properties
        )
        
        logger.info(f"Created todo: {title}")
        return f"Successfully added todo: '{title}'" + (f" (due: {due_date})" if due_date else "")
        
    except Exception as e:
        logger.error(f"Failed to add todo: {e}")
        return f"Error adding todo: {str(e)}"


@tool
def get_todos(
    status: Optional[str] = None,
    limit: int = 10,
    database_id: Optional[str] = None,
) -> str:
    """
    Get todos from Notion.
    
    Args:
        status: Filter by status - "Not started", "In progress", "Done", or None for all
        limit: Maximum number of todos to return
        database_id: Notion database ID for todos
    
    Returns:
        List of todos or error message
    """
    log_tool_call("get_todos", {"status": status or "all", "limit": limit})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    db_id = database_id or os.getenv("NOTION_TODO_DB")
    if not db_id:
        return "Error: No todo database configured. Please set NOTION_TODO_DB environment variable."
    
    try:
        body = {"page_size": limit}
        if status:
            body["filter"] = {
                "property": "Status",
                "select": {"equals": status}
            }
        
        # Use direct HTTP call since notion-client's request method has issues
        results = query_notion_database(db_id, body)
        
        if not results.get("results"):
            return "No todos found." + (f" (filtered by status: {status})" if status else "")
        
        todos = []
        for item in results["results"]:
            props = item.get("properties", {})
            
            # Get title
            title = "Untitled"
            if "Name" in props and props["Name"].get("title"):
                title = props["Name"]["title"][0]["plain_text"]
            
            # Get status
            item_status = "Unknown"
            if "Status" in props and props["Status"].get("select"):
                item_status = props["Status"]["select"]["name"]
            
            # Get due date
            due = ""
            if "Due Date" in props and props["Due Date"].get("date"):
                due = f" (due: {props['Due Date']['date']['start']})"
            
            todos.append(f"- [{item_status}] {title}{due}")
        
        return f"Found {len(todos)} todo(s):\n" + "\n".join(todos)
        
    except Exception as e:
        logger.error(f"Failed to get todos: {e}")
        return f"Error getting todos: {str(e)}"


@tool
def update_todo(
    page_id: str,
    status: Optional[str] = None,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """
    Update an existing todo in Notion.
    
    Args:
        page_id: The Notion page ID of the todo
        status: New status - "Not started", "In progress", or "Done"
        title: New title (optional)
        due_date: New due date in YYYY-MM-DD format (optional)
    
    Returns:
        Success message or error
    """
    log_tool_call("update_todo", {"page_id": page_id, "status": status or "unchanged"})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    try:
        properties = {}
        
        if status:
            properties["Status"] = {"select": {"name": status}}
        
        if title:
            properties["Name"] = {"title": [{"text": {"content": title}}]}
        
        if due_date:
            properties["Due Date"] = {"date": {"start": due_date}}
        
        if not properties:
            return "Error: No updates specified. Provide status, title, or due_date."
        
        client.pages.update(page_id=page_id, properties=properties)
        
        updates = []
        if status:
            updates.append(f"status to '{status}'")
        if title:
            updates.append(f"title to '{title}'")
        if due_date:
            updates.append(f"due date to {due_date}")
        
        logger.info(f"Updated todo {page_id}: {', '.join(updates)}")
        return f"Successfully updated todo: {', '.join(updates)}"
        
    except Exception as e:
        logger.error(f"Failed to update todo: {e}")
        return f"Error updating todo: {str(e)}"


# ============================================
# CALENDAR TOOLS
# ============================================

@tool
def add_calendar_event(
    title: str,
    start_date: str,
    end_date: Optional[str] = None,
    description: str = "",
    database_id: Optional[str] = None,
) -> str:
    """
    Add a calendar event to Notion.
    
    Args:
        title: Event title
        start_date: Start date/time in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format
        end_date: Optional end date/time
        description: Optional event description
        database_id: Notion database ID for calendar
    
    Returns:
        Success message or error
    """
    log_tool_call("add_calendar_event", {"title": title, "date": start_date})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    db_id = database_id or os.getenv("NOTION_CALENDAR_DB")
    if not db_id:
        return "Error: No calendar database configured. Please set NOTION_CALENDAR_DB environment variable."
    
    try:
        date_value = {"start": start_date}
        if end_date:
            date_value["end"] = end_date
        
        properties = {
            "Name": {
                "title": [{"text": {"content": title}}]
            },
            "Date": {
                "date": date_value
            },
        }
        
        if description:
            properties["Description"] = {
                "rich_text": [{"text": {"content": description}}]
            }
        
        new_page = client.pages.create(
            parent={"database_id": db_id},
            properties=properties
        )
        
        logger.info(f"Created calendar event: {title} on {start_date}")
        return f"Successfully added event '{title}' on {start_date}" + (f" to {end_date}" if end_date else "")
        
    except Exception as e:
        logger.error(f"Failed to add calendar event: {e}")
        return f"Error adding event: {str(e)}"


@tool
def get_calendar_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    database_id: Optional[str] = None,
) -> str:
    """
    Get calendar events from Notion.
    
    Args:
        start_date: Filter events on or after this date (YYYY-MM-DD)
        end_date: Filter events on or before this date (YYYY-MM-DD)
        limit: Maximum events to return
        database_id: Notion database ID for calendar
    
    Returns:
        List of events or error message
    """
    log_tool_call("get_calendar_events", {"start": start_date or "today", "end": end_date or "none"})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    db_id = database_id or os.getenv("NOTION_CALENDAR_DB")
    if not db_id:
        return "Error: No calendar database configured. Please set NOTION_CALENDAR_DB environment variable."
    
    try:
        filters = []
        if start_date:
            filters.append({
                "property": "Date",
                "date": {"on_or_after": start_date}
            })
        if end_date:
            filters.append({
                "property": "Date",
                "date": {"on_or_before": end_date}
            })
        
        body = {"page_size": limit}
        if filters:
            if len(filters) == 1:
                body["filter"] = filters[0]
            else:
                body["filter"] = {"and": filters}
        
        # Use direct HTTP call since notion-client's request method has issues
        results = query_notion_database(db_id, body)
        
        if not results.get("results"):
            return "No events found for the specified date range."
        
        events = []
        for item in results["results"]:
            props = item.get("properties", {})
            
            title = "Untitled Event"
            if "Name" in props and props["Name"].get("title"):
                title = props["Name"]["title"][0]["plain_text"]
            
            date_str = "No date"
            if "Date" in props and props["Date"].get("date"):
                date_info = props["Date"]["date"]
                date_str = date_info.get("start", "No date")
                if date_info.get("end"):
                    date_str += f" to {date_info['end']}"
            
            events.append(f"- {title}: {date_str}")
        
        return f"Found {len(events)} event(s):\n" + "\n".join(events)
        
    except Exception as e:
        logger.error(f"Failed to get calendar events: {e}")
        return f"Error getting events: {str(e)}"


@tool
def update_calendar_event(
    page_id: str,
    title: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    Update a calendar event in Notion.
    
    Args:
        page_id: The Notion page ID of the event
        title: New title (optional)
        start_date: New start date (optional)
        end_date: New end date (optional)
        description: New description (optional)
    
    Returns:
        Success message or error
    """
    log_tool_call("update_calendar_event", {"page_id": page_id})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    try:
        properties = {}
        
        if title:
            properties["Name"] = {"title": [{"text": {"content": title}}]}
        
        if start_date:
            date_value = {"start": start_date}
            if end_date:
                date_value["end"] = end_date
            properties["Date"] = {"date": date_value}
        
        if description:
            properties["Description"] = {"rich_text": [{"text": {"content": description}}]}
        
        if not properties:
            return "Error: No updates specified."
        
        client.pages.update(page_id=page_id, properties=properties)
        
        logger.info(f"Updated calendar event {page_id}")
        return f"Successfully updated event"
        
    except Exception as e:
        logger.error(f"Failed to update calendar event: {e}")
        return f"Error updating event: {str(e)}"


@tool
def delete_calendar_event(page_id: str) -> str:
    """
    Delete (archive) a calendar event in Notion.
    
    Args:
        page_id: The Notion page ID of the event to delete
    
    Returns:
        Success message or error
    """
    log_tool_call("delete_calendar_event", {"page_id": page_id})
    client = get_notion_client()
    if not client:
        return "Error: Notion is not configured. Please set NOTION_TOKEN."
    
    try:
        client.pages.update(page_id=page_id, archived=True)
        logger.info(f"Deleted calendar event {page_id}")
        return "Successfully deleted event"
        
    except Exception as e:
        logger.error(f"Failed to delete calendar event: {e}")
        return f"Error deleting event: {str(e)}"
