"""
Zero Me - Visual Intelligence Tools
Tools for screen capture and visual analysis using Gemini Vision
"""

import os
import sys
import base64
import tempfile
from typing import Optional
from langchain.tools import tool
from loguru import logger

# Import colorful logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logging_utils import log_tool_call, log_tool_result

# Try to import screenshot library
try:
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    logger.warning("pyautogui not installed - screen capture will be disabled")

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not installed - image processing will be limited")


def capture_screen_base64(region: Optional[tuple] = None) -> Optional[str]:
    """
    Capture the screen and return as base64 encoded JPEG.
    
    Args:
        region: Optional tuple (x, y, width, height) to capture specific region
    
    Returns:
        Base64 encoded JPEG string or None on failure
    """
    if not SCREENSHOT_AVAILABLE or not PIL_AVAILABLE:
        return None
    
    try:
        # Take screenshot
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
        
        # Convert to JPEG and encode as base64
        buffer = io.BytesIO()
        screenshot.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    except Exception as e:
        logger.error(f"Screen capture failed: {e}")
        return None


def analyze_image_with_gemini(image_base64: str, prompt: str) -> str:
    """
    Analyze an image using Gemini Vision.
    
    Args:
        image_base64: Base64 encoded image
        prompt: Analysis prompt
    
    Returns:
        Analysis result from Gemini
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Error: GOOGLE_API_KEY not configured"
        
        genai.configure(api_key=api_key)
        
        # Use gemini-2.0-flash for vision
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        
        # Create the image part
        image_part = {
            "mime_type": "image/jpeg",
            "data": image_base64
        }
        
        # Generate content
        response = model.generate_content([prompt, image_part])
        
        return response.text
    
    except Exception as e:
        logger.error(f"Gemini vision analysis failed: {e}")
        return f"Error analyzing image: {str(e)}"


@tool
def see_screen(
    task: str = "Describe what you see on the screen",
    region: Optional[str] = None,
) -> str:
    """
    Capture and analyze what's currently visible on the user's screen.
    Use this when the user asks about what they're seeing or needs help with something visual.
    
    Examples of when to use:
    - "What's on my screen right now?"
    - "Can you read this text for me?"
    - "What application am I using?"
    - "Can you translate what I'm seeing?"
    - "Help me understand this diagram"
    - "What error message is showing?"
    
    Args:
        task: What to analyze or look for in the screen capture
              (e.g., "translate the text", "describe the UI", "read the error message")
        region: Optional region to capture as "x,y,width,height" string
                If not specified, captures the entire screen
    
    Returns:
        Analysis of the screen content based on the task
    """
    log_tool_call("see_screen", {"task": task[:50], "region": region})
    
    if not SCREENSHOT_AVAILABLE:
        result = "Screen capture is not available. Please install pyautogui: pip install pyautogui"
        log_tool_result("see_screen", result, success=False)
        return result
    
    if not PIL_AVAILABLE:
        result = "Image processing is not available. Please install Pillow: pip install Pillow"
        log_tool_result("see_screen", result, success=False)
        return result
    
    # Parse region if provided
    capture_region = None
    if region:
        try:
            parts = [int(x.strip()) for x in region.split(",")]
            if len(parts) == 4:
                capture_region = tuple(parts)
        except ValueError:
            logger.warning(f"Invalid region format: {region}")
    
    # Capture screen
    logger.info("📸 Capturing screen...")
    image_base64 = capture_screen_base64(capture_region)
    
    if not image_base64:
        result = "Failed to capture screen. Make sure you have screen recording permissions enabled."
        log_tool_result("see_screen", result, success=False)
        return result
    
    # Build the analysis prompt
    analysis_prompt = f"""You are a helpful assistant analyzing a screenshot from the user's computer.

Task: {task}

Please analyze this screenshot and provide:
1. A brief description of what you see
2. Any relevant text content
3. Specific answers to the user's task

Keep your response conversational and helpful. If you see any text in a foreign language and the user asked for translation, provide the translation.
If there's an error message, explain what it means and suggest solutions.
Be specific about UI elements, buttons, and content you can identify."""

    logger.info("🔍 Analyzing screen content with Gemini Vision...")
    analysis = analyze_image_with_gemini(image_base64, analysis_prompt)
    
    if analysis.startswith("Error"):
        log_tool_result("see_screen", analysis, success=False)
    else:
        log_tool_result("see_screen", f"Analysis complete: {analysis[:100]}...")
    
    return analysis


@tool
def translate_screen(
    target_language: str = "English",
    region: Optional[str] = None,
) -> str:
    """
    Capture the screen and translate any visible text to the target language.
    
    Use this when the user asks to translate what they're seeing or when
    they need help understanding text in a foreign language on screen.
    
    Args:
        target_language: The language to translate to (default: English)
        region: Optional region to capture as "x,y,width,height" string
    
    Returns:
        Translation of visible text
    """
    log_tool_call("translate_screen", {"target_language": target_language, "region": region})
    
    if not SCREENSHOT_AVAILABLE or not PIL_AVAILABLE:
        result = "Screen capture/image processing not available."
        log_tool_result("translate_screen", result, success=False)
        return result
    
    # Parse region
    capture_region = None
    if region:
        try:
            parts = [int(x.strip()) for x in region.split(",")]
            if len(parts) == 4:
                capture_region = tuple(parts)
        except ValueError:
            pass
    
    # Capture screen
    image_base64 = capture_screen_base64(capture_region)
    
    if not image_base64:
        result = "Failed to capture screen."
        log_tool_result("translate_screen", result, success=False)
        return result
    
    # Build translation prompt
    prompt = f"""Look at this screenshot and translate any visible text to {target_language}.

Instructions:
1. Identify all readable text in the image
2. Translate each piece of text to {target_language}
3. Maintain the original structure/context
4. If text is already in {target_language}, just describe what you see

Format your response as:
- Original text locations and their translations
- A summary of the main content"""

    analysis = analyze_image_with_gemini(image_base64, prompt)
    
    if analysis.startswith("Error"):
        log_tool_result("translate_screen", analysis, success=False)
    else:
        log_tool_result("translate_screen", f"Translation complete")
    
    return analysis


@tool 
def read_screen_text(region: Optional[str] = None) -> str:
    """
    Capture the screen and extract all visible text (OCR-like functionality).
    
    Use this when the user asks to read what's on screen or needs text extracted.
    
    Args:
        region: Optional region to capture as "x,y,width,height" string
    
    Returns:
        All readable text from the screen
    """
    log_tool_call("read_screen_text", {"region": region})
    
    if not SCREENSHOT_AVAILABLE or not PIL_AVAILABLE:
        result = "Screen capture not available."
        log_tool_result("read_screen_text", result, success=False)
        return result
    
    # Parse region
    capture_region = None
    if region:
        try:
            parts = [int(x.strip()) for x in region.split(",")]
            if len(parts) == 4:
                capture_region = tuple(parts)
        except ValueError:
            pass
    
    # Capture screen
    image_base64 = capture_screen_base64(capture_region)
    
    if not image_base64:
        result = "Failed to capture screen."
        log_tool_result("read_screen_text", result, success=False)
        return result
    
    # OCR prompt
    prompt = """Extract all readable text from this screenshot.

Instructions:
1. Read all visible text content
2. Maintain the reading order (top to bottom, left to right)
3. Include button labels, menu items, and any other text
4. Preserve paragraphs and formatting where possible

Return the extracted text as plain text."""

    analysis = analyze_image_with_gemini(image_base64, prompt)
    
    if analysis.startswith("Error"):
        log_tool_result("read_screen_text", analysis, success=False)
    else:
        log_tool_result("read_screen_text", f"Text extracted: {len(analysis)} chars")
    
    return analysis


@tool
def describe_ui(
    focus: str = "general overview",
) -> str:
    """
    Capture and describe the current user interface for accessibility or help purposes.
    
    Use this when:
    - User needs help navigating an application
    - User asks what buttons/options are available
    - User needs UI guidance
    
    Args:
        focus: What aspect of the UI to focus on
               (e.g., "main menu", "toolbar", "settings", "buttons")
    
    Returns:
        Description of the UI with actionable guidance
    """
    log_tool_call("describe_ui", {"focus": focus})
    
    if not SCREENSHOT_AVAILABLE or not PIL_AVAILABLE:
        result = "Screen capture not available."
        log_tool_result("describe_ui", result, success=False)
        return result
    
    # Capture full screen
    image_base64 = capture_screen_base64()
    
    if not image_base64:
        result = "Failed to capture screen."
        log_tool_result("describe_ui", result, success=False)
        return result
    
    # UI description prompt
    prompt = f"""Describe the user interface shown in this screenshot.

Focus area: {focus}

Provide:
1. What application/website is being shown
2. Key UI elements visible (menus, buttons, panels)
3. Current state (what's selected, what mode it's in)
4. Actionable guidance based on the focus area

Keep it practical and helpful for someone who wants to know what's on their screen
and what actions they can take."""

    analysis = analyze_image_with_gemini(image_base64, prompt)
    
    if analysis.startswith("Error"):
        log_tool_result("describe_ui", analysis, success=False)
    else:
        log_tool_result("describe_ui", f"UI described")
    
    return analysis
