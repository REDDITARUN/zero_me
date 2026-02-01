"""
Comprehensive test suite for all Zero Me tools
Run with: python test_tools.py
"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
import sys

# Configure clean logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)

load_dotenv(".env.local")


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = ""):
    """Print a test result."""
    icon = "✓" if success else "✗"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{icon}{reset} {name}")
    if message:
        print(f"  → {message[:100]}{'...' if len(message) > 100 else ''}")


# ============================================
# NOTION TOOLS TESTS
# ============================================

def test_notion_search():
    """Test Notion search functionality."""
    print_header("NOTION TOOLS - Search")
    
    if not os.getenv("NOTION_TOKEN"):
        print_result("Notion Search", False, "NOTION_TOKEN not set")
        return False
    
    try:
        from tools.notion_tools import search_notion
        
        result = search_notion.invoke({"query": "test", "filter_type": "page"})
        success = "Error" not in result
        print_result("search_notion()", success, result)
        return success
    except Exception as e:
        print_result("search_notion()", False, str(e))
        return False


def test_notion_todo():
    """Test Notion todo tools."""
    print_header("NOTION TOOLS - Todo")
    
    if not os.getenv("NOTION_TOKEN"):
        print_result("Todo Tools", False, "NOTION_TOKEN not set")
        return False
    
    if not os.getenv("NOTION_TODO_DB"):
        print_result("Todo Tools", False, "NOTION_TODO_DB not set")
        return False
    
    results = []
    
    try:
        from tools.notion_tools import add_todo, get_todos, update_todo
        
        # Test add_todo
        logger.info("Testing add_todo...")
        result = add_todo.invoke({
            "title": f"Test Todo {datetime.now().strftime('%H:%M:%S')}",
            "description": "Created by test_tools.py",
            "due_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        })
        success = "Successfully" in result or "Error" not in result
        print_result("add_todo()", success, result)
        results.append(success)
        
        # Test get_todos
        logger.info("Testing get_todos...")
        result = get_todos.invoke({"limit": 5})
        success = "Error" not in result
        print_result("get_todos()", success, result)
        results.append(success)
        
        # Test get_todos with status filter
        logger.info("Testing get_todos with filter...")
        result = get_todos.invoke({"status": "Not started", "limit": 3})
        success = "Error" not in result
        print_result("get_todos(status='Not started')", success, result)
        results.append(success)
        
        return all(results)
    except Exception as e:
        print_result("Todo Tools", False, str(e))
        return False


def test_notion_calendar():
    """Test Notion calendar tools."""
    print_header("NOTION TOOLS - Calendar")
    
    if not os.getenv("NOTION_TOKEN"):
        print_result("Calendar Tools", False, "NOTION_TOKEN not set")
        return False
    
    if not os.getenv("NOTION_CALENDAR_DB"):
        print_result("Calendar Tools", False, "NOTION_CALENDAR_DB not set")
        return False
    
    results = []
    
    try:
        from tools.notion_tools import add_calendar_event, get_calendar_events
        
        # Test add_calendar_event
        logger.info("Testing add_calendar_event...")
        event_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        result = add_calendar_event.invoke({
            "title": f"Test Event {datetime.now().strftime('%H:%M:%S')}",
            "start_date": event_date,
            "description": "Created by test_tools.py"
        })
        success = "Successfully" in result or "Error" not in result
        print_result("add_calendar_event()", success, result)
        results.append(success)
        
        # Test get_calendar_events
        logger.info("Testing get_calendar_events...")
        result = get_calendar_events.invoke({"limit": 5})
        success = "Error" not in result
        print_result("get_calendar_events()", success, result)
        results.append(success)
        
        # Test get_calendar_events with date filter
        logger.info("Testing get_calendar_events with date filter...")
        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = get_calendar_events.invoke({
            "start_date": start,
            "end_date": end,
            "limit": 5
        })
        success = "Error" not in result
        print_result(f"get_calendar_events({start} to {end})", success, result)
        results.append(success)
        
        return all(results)
    except Exception as e:
        print_result("Calendar Tools", False, str(e))
        return False


def test_notion_doc():
    """Test Notion document tools."""
    print_header("NOTION TOOLS - Documents")
    
    if not os.getenv("NOTION_TOKEN"):
        print_result("Doc Tools", False, "NOTION_TOKEN not set")
        return False
    
    parent_id = os.getenv("NOTION_DOC_PARENT")
    if not parent_id:
        print_result("Doc Tools", False, "NOTION_DOC_PARENT not set - documents need a parent page")
        return False
    
    results = []
    
    try:
        from tools.notion_tools import create_notion_page, read_notion_page
        
        # Test create_notion_page
        logger.info("Testing create_notion_page...")
        result = create_notion_page.invoke({
            "title": f"Test Doc {datetime.now().strftime('%H:%M:%S')}",
            "content": "This document was created by test_tools.py for testing purposes.",
            "parent_page_id": parent_id
        })
        success = "Successfully" in result
        print_result("create_notion_page()", success, result)
        results.append(success)
        
        # Extract page ID if created successfully
        if success and "Page ID:" in result:
            page_id = result.split("Page ID:")[-1].strip()
            
            # Test read_notion_page
            logger.info("Testing read_notion_page...")
            result = read_notion_page.invoke({"page_id": page_id})
            success = "Error" not in result
            print_result("read_notion_page()", success, result)
            results.append(success)
        
        return all(results)
    except Exception as e:
        print_result("Doc Tools", False, str(e))
        return False


# ============================================
# MEMORY TOOLS TESTS
# ============================================

def test_memory_tools():
    """Test Redis memory tools."""
    print_header("MEMORY TOOLS - Redis")
    
    try:
        from memory import get_memory_manager
        memory = get_memory_manager()
        
        if not memory.is_available():
            print_result("Memory Tools", False, "Redis not available")
            return False
        
        print_result("Redis Connection", True, "Connected")
    except Exception as e:
        print_result("Memory Tools", False, f"Redis connection failed: {e}")
        return False
    
    results = []
    test_user = "test_user_tools"
    
    try:
        from tools.memory_tools import store_memory, retrieve_memory, search_memory, delete_memory
        
        # Test store_memory
        logger.info("Testing store_memory...")
        result = store_memory.invoke({
            "context_key": "test_preference",
            "context_value": "likes coffee",
            "user_id": test_user
        })
        success = "remember" in result.lower() or "Error" not in result
        print_result("store_memory()", success, result)
        results.append(success)
        
        # Test retrieve_memory (specific key)
        logger.info("Testing retrieve_memory (specific)...")
        result = retrieve_memory.invoke({
            "context_key": "test_preference",
            "user_id": test_user
        })
        success = "coffee" in result.lower() or "remember" in result.lower()
        print_result("retrieve_memory(key)", success, result)
        results.append(success)
        
        # Test retrieve_memory (all)
        logger.info("Testing retrieve_memory (all)...")
        result = retrieve_memory.invoke({"user_id": test_user})
        success = "Error" not in result
        print_result("retrieve_memory(all)", success, result)
        results.append(success)
        
        # Test search_memory
        logger.info("Testing search_memory...")
        result = search_memory.invoke({
            "query": "coffee",
            "user_id": test_user
        })
        success = "Error" not in result
        print_result("search_memory()", success, result)
        results.append(success)
        
        # Test delete_memory
        logger.info("Testing delete_memory...")
        result = delete_memory.invoke({
            "context_key": "test_preference",
            "user_id": test_user
        })
        success = "Deleted" in result or "Error" not in result
        print_result("delete_memory()", success, result)
        results.append(success)
        
        return all(results)
    except Exception as e:
        print_result("Memory Tools", False, str(e))
        return False


# ============================================
# ANALYTICS TOOLS TESTS
# ============================================

def test_analytics_tools():
    """Test WandB analytics tools."""
    print_header("ANALYTICS TOOLS - WandB")
    
    if not os.getenv("WANDB_API_KEY"):
        print_result("Analytics Tools", False, "WANDB_API_KEY not set")
        return False
    
    results = []
    
    try:
        from tools.analytics_tools import (
            log_metric, 
            log_question_count, 
            get_current_parameters
        )
        
        # Test log_metric
        logger.info("Testing log_metric...")
        result = log_metric.invoke({
            "metric_name": "test_metric",
            "value": 42.0
        })
        success = "Logged" in result
        print_result("log_metric()", success, result)
        results.append(success)
        
        # Test log_question_count
        logger.info("Testing log_question_count...")
        result = log_question_count.invoke({
            "count": 3,
            "conversation_topic": "testing"
        })
        success = "Logged" in result
        print_result("log_question_count()", success, result)
        results.append(success)
        
        # Test get_current_parameters
        logger.info("Testing get_current_parameters...")
        result = get_current_parameters.invoke({})
        success = "voice_agent" in result or "Parameters" in result
        print_result("get_current_parameters()", success, result)
        results.append(success)
        
        return all(results)
    except Exception as e:
        print_result("Analytics Tools", False, str(e))
        return False


# ============================================
# EMAIL TOOLS TESTS
# ============================================

def test_email_tools():
    """Test Resend email tools."""
    print_header("EMAIL TOOLS - Resend")
    
    if not os.getenv("RESEND_API_KEY"):
        print_result("Email Tools", False, "RESEND_API_KEY not set (skipping)")
        return True  # Skip but don't fail
    
    results = []
    
    try:
        from tools.email_tools import draft_email
        
        # Test draft_email (doesn't actually send)
        logger.info("Testing draft_email...")
        result = draft_email.invoke({
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "This is a test email body."
        })
        success = "draft" in result.lower() or "EMAIL DRAFT" in result
        print_result("draft_email()", success, result)
        results.append(success)
        
        # Note: We don't test send_email to avoid actually sending emails
        print_result("send_email()", True, "Skipped (would send real email)")
        
        return all(results)
    except Exception as e:
        print_result("Email Tools", False, str(e))
        return False


# ============================================
# MAIN TEST RUNNER
# ============================================

def main():
    """Run all tool tests."""
    print("\n" + "=" * 60)
    print("  ZERO ME - TOOL TEST SUITE")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    results = {
        "Notion Search": test_notion_search(),
        "Notion Todo": test_notion_todo(),
        "Notion Calendar": test_notion_calendar(),
        "Notion Documents": test_notion_doc(),
        "Memory (Redis)": test_memory_tools(),
        "Analytics (WandB)": test_analytics_tools(),
        "Email (Resend)": test_email_tools(),
    }
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        icon = "✓" if success else "✗"
        color = "\033[92m" if success else "\033[91m"
        reset = "\033[0m"
        print(f"  {color}{icon}{reset} {name}")
    
    print()
    print(f"  Passed: {passed}/{total}")
    
    if passed == total:
        print("\n  \033[92m🎉 All tests passed!\033[0m\n")
    else:
        print(f"\n  \033[93m⚠ {total - passed} test(s) need attention\033[0m\n")


if __name__ == "__main__":
    main()
