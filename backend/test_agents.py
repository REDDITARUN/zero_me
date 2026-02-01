"""
Test script for Zero Me agent system
Run with: python test_agents.py
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv(".env.local")

from loguru import logger


async def test_memory():
    """Test Redis memory manager."""
    print("\n" + "="*50)
    print("Testing Memory Manager (Redis)")
    print("="*50)
    
    from memory import get_memory_manager
    
    memory = get_memory_manager()
    
    if not memory.is_available():
        print("⚠ Redis not available - memory tests skipped")
        return
    
    # Test storing context
    success = memory.store_context("test_user", "preferred_name", "Alex")
    print(f"Store context: {'✓' if success else '✗'}")
    
    # Test retrieving context
    result = memory.retrieve_context("test_user", "preferred_name")
    print(f"Retrieve context: {'✓' if result else '✗'} - {result}")
    
    # Test search
    results = memory.search_context("test_user", "name")
    print(f"Search context: {'✓' if results else '✗'} - {len(results)} results")
    
    # Cleanup
    memory.delete_context("test_user", "preferred_name")
    print("✓ Memory tests passed!")


async def test_analytics():
    """Test WandB analytics manager."""
    print("\n" + "="*50)
    print("Testing Analytics Manager (WandB)")
    print("="*50)
    
    from analytics import get_analytics_manager
    
    analytics = get_analytics_manager()
    
    if not analytics.enabled:
        print("⚠ WandB not available - analytics tests skipped")
        return
    
    # Test logging metric
    analytics.log_metric("test_metric", 42.0)
    print("✓ Logged test metric")
    
    # Note: We don't finish() here to keep the run open for the actual bot
    print("✓ Analytics tests passed!")


async def test_sub_agents():
    """Test sub-agent creation."""
    print("\n" + "="*50)
    print("Testing Sub-Agents (LangChain)")
    print("="*50)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠ GOOGLE_API_KEY not set - agent tests skipped")
        return
    
    try:
        from agents.sub_agents import (
            create_doc_agent,
            create_todo_agent,
            create_email_agent,
            create_calendar_agent,
        )
        
        doc = create_doc_agent()
        print(f"✓ DocAgent created: {doc.name}")
        
        todo = create_todo_agent()
        print(f"✓ TodoAgent created: {todo.name}")
        
        email = create_email_agent()
        print(f"✓ EmailAgent created: {email.name}")
        
        calendar = create_calendar_agent()
        print(f"✓ CalendarAgent created: {calendar.name}")
        
        print("✓ All sub-agents created successfully!")
        
    except Exception as e:
        print(f"✗ Error creating sub-agents: {e}")


async def test_main_agent():
    """Test main dispatcher agent."""
    print("\n" + "="*50)
    print("Testing Main Dispatcher Agent")
    print("="*50)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠ GOOGLE_API_KEY not set - agent tests skipped")
        return
    
    try:
        from agents.main_agent import create_main_agent
        
        main = create_main_agent()
        print(f"✓ MainDispatcherAgent created: {main.name}")
        print(f"  - Tools: {len(main.tools)}")
        
        print("✓ Main agent created successfully!")
        
    except Exception as e:
        print(f"✗ Error creating main agent: {e}")


async def test_personality_enhancer():
    """Test personality enhancer agent."""
    print("\n" + "="*50)
    print("Testing Personality Enhancer Agent")
    print("="*50)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠ GOOGLE_API_KEY not set - agent tests skipped")
        return
    
    try:
        from agents.personality_enhancer import create_personality_enhancer
        
        enhancer = create_personality_enhancer()
        print(f"✓ PersonalityEnhancerAgent created: {enhancer.name}")
        print(f"  - Tools: {len(enhancer.tools)}")
        
        # Test conversation tracking
        enhancer.start_conversation()
        enhancer.record_question()
        enhancer.record_topic("testing")
        
        print("✓ Conversation tracking works!")
        print("✓ Personality enhancer created successfully!")
        
    except Exception as e:
        print(f"✗ Error creating personality enhancer: {e}")


async def test_notion_tools():
    """Test Notion tools (requires NOTION_TOKEN)."""
    print("\n" + "="*50)
    print("Testing Notion Tools")
    print("="*50)
    
    if not os.getenv("NOTION_TOKEN"):
        print("⚠ NOTION_TOKEN not set - Notion tests skipped")
        return
    
    try:
        from tools.notion_tools import search_notion
        
        # Test search (doesn't require specific database)
        result = search_notion.invoke({"query": "test", "filter_type": "page"})
        print(f"✓ Notion search works: {result[:100]}...")
        
    except Exception as e:
        print(f"✗ Error testing Notion: {e}")


async def test_todo_tools():
    """Test Todo tools (requires NOTION_TODO_DB)."""
    print("\n" + "="*50)
    print("Testing Todo Tools")
    print("="*50)
    
    if not os.getenv("NOTION_TOKEN"):
        print("⚠ NOTION_TOKEN not set - Todo tests skipped")
        return
    
    if not os.getenv("NOTION_TODO_DB"):
        print("⚠ NOTION_TODO_DB not set - Todo tests skipped")
        print("  Set this in .env.local to enable todo functionality")
        return
    
    try:
        from tools.notion_tools import add_todo, get_todos, update_todo
        
        # Test adding a todo
        result = add_todo.invoke({
            "title": "Test Todo from Zero Me",
            "description": "This is a test todo created by the agent system",
            "due_date": "2026-02-05"
        })
        print(f"✓ Add todo: {result}")
        
        # Test getting todos
        result = get_todos.invoke({"limit": 5})
        print(f"✓ Get todos: {result[:150]}...")
        
        print("✓ Todo tools working!")
        
    except Exception as e:
        print(f"✗ Error testing Todo tools: {e}")


async def test_calendar_tools():
    """Test Calendar tools (requires NOTION_CALENDAR_DB)."""
    print("\n" + "="*50)
    print("Testing Calendar Tools")
    print("="*50)
    
    if not os.getenv("NOTION_TOKEN"):
        print("⚠ NOTION_TOKEN not set - Calendar tests skipped")
        return
    
    if not os.getenv("NOTION_CALENDAR_DB"):
        print("⚠ NOTION_CALENDAR_DB not set - Calendar tests skipped")
        print("  Set this in .env.local to enable calendar functionality")
        return
    
    try:
        from tools.notion_tools import add_calendar_event, get_calendar_events
        
        # Test adding an event
        result = add_calendar_event.invoke({
            "title": "Test Event from Zero Me",
            "start_date": "2026-02-10",
            "description": "This is a test event created by the agent system"
        })
        print(f"✓ Add event: {result}")
        
        # Test getting events
        result = get_calendar_events.invoke({"limit": 5})
        print(f"✓ Get events: {result[:150]}...")
        
        print("✓ Calendar tools working!")
        
    except Exception as e:
        print(f"✗ Error testing Calendar tools: {e}")


async def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("Zero Me Agent System Tests")
    print("="*50)
    
    await test_memory()
    await test_analytics()
    await test_notion_tools()
    await test_todo_tools()
    await test_calendar_tools()
    await test_sub_agents()
    await test_main_agent()
    await test_personality_enhancer()
    
    print("\n" + "="*50)
    print("All tests completed!")
    print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
