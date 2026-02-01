#!/usr/bin/env python3
"""
Comprehensive test suite for all Zero Me tools.
Tests: Email, Memory, Notion (Todo, Calendar, Doc), Analytics

Run with: python test_all_tools.py
"""
import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv(".env.local", override=True)

# Configure logger
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<level>{level: <8}</level> | {message}",
    level="INFO",
    colorize=True
)


def header(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def subheader(title: str):
    """Print a subsection header."""
    print(f"\n--- {title} ---")


async def test_email_tools():
    """Test email tools with Resend."""
    header("EMAIL TOOLS TEST")
    
    from tools.email_tools import send_email, draft_email, check_email_status
    
    test_email = "rbchstarun@gmail.com"
    
    # Test 1: Draft an email
    subheader("Test 1: Draft Email")
    try:
        result = draft_email.invoke({
            "to": test_email,
            "subject": "Test Draft from Zero Me",
            "body": "This is a test draft email from your Zero Me assistant.\n\nBest regards,\nCasey"
        })
        logger.info(f"Draft result: {result}")
        print(f"✅ Draft created successfully")
    except Exception as e:
        logger.error(f"Draft failed: {e}")
        print(f"❌ Draft failed: {e}")
    
    # Test 2: Send an actual email
    subheader("Test 2: Send Email")
    try:
        result = send_email.invoke({
            "to": test_email,
            "subject": f"Zero Me Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "body": """Hello!

This is a test email from your Zero Me assistant to verify the email integration is working correctly.

Test details:
- Timestamp: """ + datetime.now().isoformat() + """
- Sent via: Resend API
- Agent: Zero Me Voice Assistant

If you received this email, the email tools are working! 🎉

Best regards,
Casey (Your Zero Me Assistant)"""
        })
        logger.info(f"Send result: {result}")
        if "successfully" in result.lower() or "id" in result.lower():
            print(f"✅ Email sent successfully to {test_email}")
        else:
            print(f"⚠️ Email result: {result}")
    except Exception as e:
        logger.error(f"Send failed: {e}")
        print(f"❌ Send failed: {e}")
    
    # Test 3: Check email status (if we have an ID)
    subheader("Test 3: Check Email Status")
    try:
        # This will likely fail without a real email ID, but tests the function
        result = check_email_status.invoke({"email_id": "test-id-123"})
        logger.info(f"Status result: {result}")
        print(f"✅ Status check completed: {result[:100]}...")
    except Exception as e:
        logger.error(f"Status check info: {e}")
        print(f"ℹ️ Status check: {e}")


async def test_memory_tools():
    """Test memory tools with Redis."""
    header("MEMORY TOOLS TEST")
    
    from tools.memory_tools import store_memory, retrieve_memory, search_memory, delete_memory, get_conversation_history
    
    user_id = "test_user_tarun"
    
    # Test 1: Store memories
    subheader("Test 1: Store Memories")
    memories_to_store = [
        {"context_key": "favorite_color", "context_value": "Blue is Tarun's favorite color"},
        {"context_key": "work_schedule", "context_value": "Tarun works from 9 AM to 6 PM on weekdays"},
        {"context_key": "coffee_preference", "context_value": "Tarun likes his coffee black with no sugar"},
        {"context_key": "project_focus", "context_value": "Currently working on Zero Me AI assistant project"},
    ]
    
    for mem in memories_to_store:
        try:
            result = store_memory.invoke({
                "context_key": mem["context_key"],
                "context_value": mem["context_value"],
            })
            logger.info(f"Stored '{mem['context_key']}': {result}")
            print(f"✅ Stored: {mem['context_key']}")
        except Exception as e:
            logger.error(f"Store failed for {mem['context_key']}: {e}")
            print(f"❌ Failed to store {mem['context_key']}: {e}")
    
    # Test 2: Retrieve specific memory
    subheader("Test 2: Retrieve Memory")
    try:
        result = retrieve_memory.invoke({
            "context_key": "favorite_color"
        })
        logger.info(f"Retrieved: {result}")
        print(f"✅ Retrieved favorite_color: {result}")
    except Exception as e:
        logger.error(f"Retrieve failed: {e}")
        print(f"❌ Retrieve failed: {e}")
    
    # Test 3: Search memories
    subheader("Test 3: Search Memories")
    try:
        result = search_memory.invoke({
            "query": "coffee"
        })
        logger.info(f"Search result: {result}")
        print(f"✅ Search 'coffee': {result}")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        print(f"❌ Search failed: {e}")
    
    # Test 4: Get conversation history
    subheader("Test 4: Conversation History")
    try:
        result = get_conversation_history.invoke({
            "limit": 5
        })
        logger.info(f"History: {result}")
        print(f"✅ Got conversation history")
    except Exception as e:
        logger.error(f"History failed: {e}")
        print(f"❌ History failed: {e}")
    
    # Test 5: Delete a memory
    subheader("Test 5: Delete Memory")
    try:
        result = delete_memory.invoke({
            "context_key": "favorite_color"  # We'll re-add this
        })
        logger.info(f"Delete result: {result}")
        print(f"✅ Deleted favorite_color")
        
        # Re-store it
        store_memory.invoke({
            "context_key": "favorite_color",
            "context_value": "Blue is Tarun's favorite color",
        })
        print(f"✅ Re-stored favorite_color")
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        print(f"❌ Delete failed: {e}")


async def test_notion_tools():
    """Test Notion tools (Todo, Calendar, Doc)."""
    header("NOTION TOOLS TEST")
    
    from tools.notion_tools import (
        add_todo, get_todos, update_todo,
        add_calendar_event, get_calendar_events, update_calendar_event, delete_calendar_event,
        create_notion_page, read_notion_page, search_notion
    )
    
    # ===== TODO TESTS =====
    subheader("TODO: Add Todo")
    todo_id = None
    try:
        result = add_todo.invoke({
            "title": f"Test Todo - {datetime.now().strftime('%H:%M:%S')}",
            "description": "This is a test todo created by the test suite",
            "due_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "status": "Not Started"
        })
        logger.info(f"Add todo result: {result}")
        # Extract ID if present
        if "id:" in result.lower() or "created" in result.lower():
            print(f"✅ Todo created: {result[:100]}...")
        else:
            print(f"⚠️ Todo result: {result[:100]}...")
    except Exception as e:
        logger.error(f"Add todo failed: {e}")
        print(f"❌ Add todo failed: {e}")
    
    subheader("TODO: Get Todos")
    try:
        result = get_todos.invoke({})
        logger.info(f"Get todos result: {result}")
        print(f"✅ Got todos: {result[:200]}...")
    except Exception as e:
        logger.error(f"Get todos failed: {e}")
        print(f"❌ Get todos failed: {e}")
    
    # ===== CALENDAR TESTS =====
    subheader("CALENDAR: Add Event")
    event_id = None
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = add_calendar_event.invoke({
            "title": f"Test Meeting - {datetime.now().strftime('%H:%M:%S')}",
            "start_date": tomorrow,
            "description": "Test calendar event from test suite"
        })
        logger.info(f"Add event result: {result}")
        print(f"✅ Calendar event created: {result[:100]}...")
    except Exception as e:
        logger.error(f"Add event failed: {e}")
        print(f"❌ Add event failed: {e}")
    
    subheader("CALENDAR: Get Events")
    try:
        result = get_calendar_events.invoke({})
        logger.info(f"Get events result: {result}")
        print(f"✅ Got calendar events: {result[:200]}...")
    except Exception as e:
        logger.error(f"Get events failed: {e}")
        print(f"❌ Get events failed: {e}")
    
    # ===== DOCUMENT TESTS =====
    subheader("DOCUMENT: Create Page")
    try:
        result = create_notion_page.invoke({
            "title": f"Test Note - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": """# Test Document

This is a test document created by the Zero Me test suite.

## Details
- Created: """ + datetime.now().isoformat() + """
- Purpose: Verify Notion integration

## Notes
The document creation is working correctly!
"""
        })
        logger.info(f"Create page result: {result}")
        print(f"✅ Document created: {result[:100]}...")
    except Exception as e:
        logger.error(f"Create page failed: {e}")
        print(f"❌ Create page failed: {e}")
    
    subheader("DOCUMENT: Search Notion")
    try:
        result = search_notion.invoke({
            "query": "Test"
        })
        logger.info(f"Search result: {result}")
        print(f"✅ Search completed: {result[:200]}...")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        print(f"❌ Search failed: {e}")


async def test_analytics_tools():
    """Test analytics tools with WandB."""
    header("ANALYTICS TOOLS TEST")
    
    from tools.analytics_tools import (
        log_metric, log_question_count, log_parameter_change,
        modify_agent_parameter, get_current_parameters, record_conversation_analytics
    )
    
    # Test 1: Log a metric
    subheader("Test 1: Log Metric")
    try:
        result = log_metric.invoke({
            "metric_name": "test_metric",
            "value": 42.5,
        })
        logger.info(f"Log metric result: {result}")
        print(f"✅ Metric logged: {result}")
    except Exception as e:
        logger.error(f"Log metric failed: {e}")
        print(f"❌ Log metric failed: {e}")
    
    # Test 2: Log question count
    subheader("Test 2: Log Question Count")
    try:
        result = log_question_count.invoke({
            "count": 5,
            "conversation_topic": "test_conversation"
        })
        logger.info(f"Question count result: {result}")
        print(f"✅ Question count logged: {result}")
    except Exception as e:
        logger.error(f"Question count failed: {e}")
        print(f"❌ Question count failed: {e}")
    
    # Test 3: Get current parameters
    subheader("Test 3: Get Parameters")
    try:
        result = get_current_parameters.invoke({})
        logger.info(f"Parameters: {result[:500]}...")
        print(f"✅ Got parameters (truncated):\n{result[:300]}...")
    except Exception as e:
        logger.error(f"Get parameters failed: {e}")
        print(f"❌ Get parameters failed: {e}")
    
    # Test 4: Record conversation analytics
    subheader("Test 4: Record Conversation Analytics")
    try:
        result = record_conversation_analytics.invoke({
            "questions_asked": 5,
            "tasks_delegated": 2,
            "duration_seconds": 120.0,
            "topics": "testing, verification, tools",  # comma-separated string
        })
        logger.info(f"Conversation analytics result: {result}")
        print(f"✅ Conversation analytics recorded: {result}")
    except Exception as e:
        logger.error(f"Conversation analytics failed: {e}")
        print(f"❌ Conversation analytics failed: {e}")
    
    # Test 5: Log parameter change
    subheader("Test 5: Log Parameter Change")
    try:
        result = log_parameter_change.invoke({
            "agent_name": "voice_agent",
            "parameter_key": "temperature",
            "old_value": "0.7",
            "new_value": "0.8",
            "reason": "Testing parameter change logging"
        })
        logger.info(f"Parameter change result: {result}")
        print(f"✅ Parameter change logged: {result}")
    except Exception as e:
        logger.error(f"Parameter change failed: {e}")
        print(f"❌ Parameter change failed: {e}")


async def test_agents():
    """Test the agent system."""
    header("AGENT SYSTEM TEST")
    
    from agents.main_agent import get_main_agent
    from agents.personality_enhancer import get_personality_enhancer
    
    # Test Main Agent
    subheader("Main Dispatcher Agent")
    try:
        main_agent = get_main_agent()
        logger.info("Main agent initialized")
        print(f"✅ Main agent initialized successfully")
        
        # Test a simple dispatch
        result = await main_agent.dispatch("Add a todo to test the agent system")
        logger.info(f"Dispatch result: {result}")
        print(f"✅ Dispatch result: {result[:200]}...")
    except Exception as e:
        logger.error(f"Main agent failed: {e}")
        print(f"❌ Main agent failed: {e}")
    
    # Test Personality Enhancer
    subheader("Personality Enhancer Agent")
    try:
        personality = get_personality_enhancer()
        logger.info("Personality enhancer initialized")
        print(f"✅ Personality enhancer initialized")
        
        # Start a test conversation
        personality.start_conversation()
        personality.record_question()
        personality.record_question()
        personality.record_task_delegation()
        personality.record_topic("testing")
        
        # End and get summary
        summary = await personality.end_conversation("test_user")
        logger.info(f"Conversation summary: {summary}")
        print(f"✅ Conversation tracked: {summary}")
    except Exception as e:
        logger.error(f"Personality enhancer failed: {e}")
        print(f"❌ Personality enhancer failed: {e}")


async def test_memory_manager():
    """Test the memory manager directly."""
    header("MEMORY MANAGER DIRECT TEST")
    
    from memory import get_memory_manager
    
    try:
        memory = get_memory_manager()
        user_id = "test_user_direct"
        
        # Store context (sync method)
        subheader("Store Context")
        success = memory.store_context(
            user_id=user_id,
            context_key="direct_test",
            context_value="This is a direct memory manager test",
            category="test"
        )
        if success:
            print(f"✅ Context stored")
        else:
            print(f"❌ Failed to store context")
        
        # Retrieve context (sync method)
        subheader("Retrieve Context")
        result = memory.retrieve_context(user_id, "direct_test")
        logger.info(f"Retrieved: {result}")
        print(f"✅ Retrieved: {result}")
        
        # Search context (sync method)
        subheader("Search Context")
        results = memory.search_context(user_id, "test")
        logger.info(f"Search results: {results}")
        print(f"✅ Search found {len(results)} results")
        
        # Store conversation summary (sync method)
        subheader("Store Conversation Summary")
        success = memory.store_conversation_summary(
            user_id=user_id,
            summary={"text": "Test conversation about memory testing"},
            topics=["memory", "testing", "redis"],
            duration=60
        )
        if success:
            print(f"✅ Conversation summary stored")
        else:
            print(f"❌ Failed to store conversation summary")
        
        # Get recent conversations (sync method)
        subheader("Get Recent Conversations")
        convos = memory.get_recent_conversations(user_id, limit=3)
        logger.info(f"Recent conversations: {convos}")
        print(f"✅ Got {len(convos)} recent conversations")
        
    except Exception as e:
        logger.error(f"Memory manager failed: {e}")
        print(f"❌ Memory manager failed: {e}")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🚀" * 35)
    print("       ZERO ME - COMPREHENSIVE TOOL TEST SUITE")
    print("🚀" * 35)
    
    # Check environment
    header("ENVIRONMENT CHECK")
    env_vars = [
        ("GOOGLE_API_KEY", bool(os.getenv("GOOGLE_API_KEY"))),
        ("NOTION_TOKEN", bool(os.getenv("NOTION_TOKEN"))),
        ("NOTION_TODO_DB", bool(os.getenv("NOTION_TODO_DB"))),
        ("NOTION_CALENDAR_DB", bool(os.getenv("NOTION_CALENDAR_DB"))),
        ("NOTION_DOC_PARENT", bool(os.getenv("NOTION_DOC_PARENT"))),
        ("RESEND_API_KEY", bool(os.getenv("RESEND_API_KEY"))),
        ("REDIS_URL", bool(os.getenv("REDIS_URL"))),
        ("WANDB_API_KEY", bool(os.getenv("WANDB_API_KEY"))),
    ]
    
    all_set = True
    for name, is_set in env_vars:
        status = "✅" if is_set else "❌"
        print(f"  {status} {name}")
        if not is_set:
            all_set = False
    
    if not all_set:
        print("\n⚠️ Some environment variables are missing. Some tests may fail.")
    
    # Run tests
    await test_memory_manager()
    await test_memory_tools()
    await test_notion_tools()
    await test_email_tools()
    await test_analytics_tools()
    await test_agents()
    
    # Summary
    header("TEST SUMMARY")
    print("""
All tests completed! Check the output above for any failures.

Key things to verify:
1. ✅ Memory: Redis storing and retrieving data
2. ✅ Notion: Todos, Calendar, Documents created
3. ✅ Email: Check rbchstarun@gmail.com for test email
4. ✅ Analytics: Check WandB dashboard for logged metrics
5. ✅ Agents: Main agent and personality enhancer working
""")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
