"""
Zero Me - Voice Control Tools
Tools for dynamically changing voice settings based on user preferences.
"""

import re
from typing import Optional, Dict, Any, Literal
from langchain_core.tools import tool
from loguru import logger
from datetime import datetime

# ============================================
# VOICE CONFIGURATION
# ============================================

# Available Gemini Live voices with their characteristics
VOICE_PROFILES = {
    # Fast/Upbeat voices
    "Puck": {"style": "Upbeat", "pace": "fast", "description": "Energetic and quick"},
    "Fenrir": {"style": "Excitable", "pace": "fast", "description": "Enthusiastic and lively"},
    "Laomedeia": {"style": "Upbeat", "pace": "fast", "description": "Cheerful and quick"},
    
    # Moderate pace voices
    "Charon": {"style": "Informative", "pace": "moderate", "description": "Clear and steady"},
    "Kore": {"style": "Firm", "pace": "moderate", "description": "Confident and measured"},
    "Algieba": {"style": "Smooth", "pace": "moderate", "description": "Flowing and balanced"},
    "Despina": {"style": "Smooth", "pace": "moderate", "description": "Even and pleasant"},
    
    # Slow/Relaxed voices
    "Enceladus": {"style": "Breathy", "pace": "slow", "description": "Calm and relaxed"},
    "Aoede": {"style": "Breezy", "pace": "slow", "description": "Laid-back and easy"},
    "Gacrux": {"style": "Mature", "pace": "slow", "description": "Thoughtful and deliberate"},
    "Achernar": {"style": "Soft", "pace": "slow", "description": "Gentle and unhurried"},
    "Zubenelgenubi": {"style": "Casual", "pace": "slow", "description": "Relaxed and casual"},
}

# Pace to recommended voices mapping
PACE_TO_VOICES = {
    "fast": ["Puck", "Fenrir", "Laomedeia"],
    "moderate": ["Charon", "Kore", "Algieba", "Despina"],
    "slow": ["Enceladus", "Aoede", "Gacrux", "Achernar"],
}

# Default voice for each pace
DEFAULT_VOICE_FOR_PACE = {
    "fast": "Puck",
    "moderate": "Charon",
    "slow": "Enceladus",
}


# ============================================
# GLOBAL VOICE STATE (Shared with bot.py)
# ============================================

class VoiceSettingsManager:
    """
    Singleton manager for voice settings that can be accessed globally.
    Allows dynamic voice changes during runtime.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Current settings
        self.current_voice_id = "Puck"
        self.current_pace = "fast"
        self.custom_prompt_additions = []
        
        # Callback for notifying bot of changes
        self._voice_change_callback = None
        self._prompt_change_callback = None
        
        # Change history for analytics
        self.change_history = []
        
        self._initialized = True
        logger.info("VoiceSettingsManager initialized")
    
    def set_voice_change_callback(self, callback):
        """Set callback to be called when voice changes."""
        self._voice_change_callback = callback
    
    def set_prompt_change_callback(self, callback):
        """Set callback to be called when prompt changes."""
        self._prompt_change_callback = callback
    
    def change_voice(self, voice_id: str, reason: str = "user_request") -> Dict[str, Any]:
        """
        Change the current voice.
        
        Args:
            voice_id: The voice ID to change to
            reason: Why the change was made
        
        Returns:
            Result dict with old and new voice info
        """
        if voice_id not in VOICE_PROFILES:
            return {
                "success": False,
                "error": f"Unknown voice: {voice_id}. Available: {list(VOICE_PROFILES.keys())}"
            }
        
        old_voice = self.current_voice_id
        old_pace = self.current_pace
        
        self.current_voice_id = voice_id
        self.current_pace = VOICE_PROFILES[voice_id]["pace"]
        
        # Record change
        change_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "voice_change",
            "old_voice": old_voice,
            "new_voice": voice_id,
            "reason": reason,
        }
        self.change_history.append(change_record)
        
        logger.info(f"🎤 Voice changed: {old_voice} → {voice_id} (reason: {reason})")
        
        # Notify bot if callback is set
        if self._voice_change_callback:
            try:
                self._voice_change_callback(voice_id)
            except Exception as e:
                logger.error(f"Voice change callback failed: {e}")
        
        return {
            "success": True,
            "old_voice": old_voice,
            "new_voice": voice_id,
            "old_pace": old_pace,
            "new_pace": self.current_pace,
            "voice_style": VOICE_PROFILES[voice_id]["style"],
        }
    
    def change_pace(self, pace: str, reason: str = "user_request") -> Dict[str, Any]:
        """
        Change voice based on pace preference.
        
        Args:
            pace: "fast", "moderate", or "slow"
            reason: Why the change was made
        
        Returns:
            Result dict
        """
        if pace not in PACE_TO_VOICES:
            return {
                "success": False,
                "error": f"Unknown pace: {pace}. Use 'fast', 'moderate', or 'slow'."
            }
        
        new_voice = DEFAULT_VOICE_FOR_PACE[pace]
        return self.change_voice(new_voice, reason=f"pace_change_{pace}: {reason}")
    
    def add_prompt_instruction(self, instruction: str, category: str = "general") -> Dict[str, Any]:
        """
        Add a custom instruction to the system prompt.
        
        Args:
            instruction: The instruction to add
            category: Category for the instruction
        
        Returns:
            Result dict
        """
        entry = {
            "instruction": instruction,
            "category": category,
            "added_at": datetime.utcnow().isoformat(),
        }
        self.custom_prompt_additions.append(entry)
        
        # Record change
        change_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "prompt_addition",
            "instruction": instruction[:100],
            "category": category,
        }
        self.change_history.append(change_record)
        
        logger.info(f"📝 Prompt instruction added: {instruction[:50]}...")
        
        # Notify if callback is set
        if self._prompt_change_callback:
            try:
                self._prompt_change_callback(self.get_custom_prompt_section())
            except Exception as e:
                logger.error(f"Prompt change callback failed: {e}")
        
        return {
            "success": True,
            "instruction": instruction,
            "total_custom_instructions": len(self.custom_prompt_additions),
        }
    
    def get_custom_prompt_section(self) -> str:
        """Get all custom prompt additions as a formatted string."""
        if not self.custom_prompt_additions:
            return ""
        
        sections = {}
        for entry in self.custom_prompt_additions:
            cat = entry["category"]
            if cat not in sections:
                sections[cat] = []
            sections[cat].append(entry["instruction"])
        
        result = "\n\n# Dynamic Personalization\n"
        for cat, instructions in sections.items():
            result += f"\n## {cat.title()}\n"
            for inst in instructions:
                result += f"- {inst}\n"
        
        return result
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current voice settings."""
        return {
            "voice_id": self.current_voice_id,
            "pace": self.current_pace,
            "voice_style": VOICE_PROFILES.get(self.current_voice_id, {}).get("style", "Unknown"),
            "custom_instructions_count": len(self.custom_prompt_additions),
            "recent_changes": self.change_history[-5:] if self.change_history else [],
        }
    
    def clear_custom_instructions(self) -> Dict[str, Any]:
        """Clear all custom prompt instructions."""
        count = len(self.custom_prompt_additions)
        self.custom_prompt_additions = []
        logger.info(f"Cleared {count} custom instructions")
        return {"success": True, "cleared_count": count}


# Global singleton instance
_voice_manager: Optional[VoiceSettingsManager] = None


def get_voice_manager() -> VoiceSettingsManager:
    """Get the global voice settings manager."""
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceSettingsManager()
    return _voice_manager


# ============================================
# VOICE PREFERENCE DETECTION
# ============================================

def detect_voice_preference(text: str) -> Optional[Dict[str, Any]]:
    """
    Detect if the user's text contains voice speed/style preferences.
    
    Args:
        text: User's transcribed text
    
    Returns:
        Dict with detected preference, or None if no preference detected
    """
    text_lower = text.lower()
    
    # Speed increase patterns
    faster_patterns = [
        r"speak(?:ing)?\s+(?:more\s+)?fast(?:er)?",
        r"talk(?:ing)?\s+(?:more\s+)?fast(?:er)?",
        r"speed\s+up",
        r"(?:go|be)\s+(?:more\s+)?quick(?:er)?",
        r"(?:can|could)\s+you\s+(?:speak|talk)\s+fast(?:er)?",
        r"too\s+slow",
        r"you(?:'re| are)\s+(?:too\s+)?slow",
        r"hurry\s+up",
        r"quicker",
    ]
    
    # Speed decrease patterns
    slower_patterns = [
        r"speak(?:ing)?\s+(?:more\s+)?slow(?:er|ly)?",
        r"talk(?:ing)?\s+(?:more\s+)?slow(?:er|ly)?",
        r"slow\s+down",
        r"(?:go|be)\s+(?:more\s+)?slow(?:er)?",
        r"(?:can|could)\s+you\s+(?:speak|talk)\s+slow(?:er|ly)?",
        r"too\s+fast",
        r"you(?:'re| are)\s+(?:too\s+)?fast",
        r"take\s+(?:your|it)\s+(?:time|slow)",
        r"calm(?:er)?\s+(?:down|voice)?",
        r"more\s+relaxed",
    ]
    
    # Check for faster preference
    for pattern in faster_patterns:
        if re.search(pattern, text_lower):
            return {
                "preference": "faster",
                "recommended_pace": "fast",
                "recommended_voice": "Puck",
                "matched_pattern": pattern,
                "original_text": text,
            }
    
    # Check for slower preference
    for pattern in slower_patterns:
        if re.search(pattern, text_lower):
            return {
                "preference": "slower",
                "recommended_pace": "slow",
                "recommended_voice": "Enceladus",
                "matched_pattern": pattern,
                "original_text": text,
            }
    
    return None


# ============================================
# LANGCHAIN TOOLS
# ============================================

@tool
def change_voice_speed(
    speed: Literal["fast", "moderate", "slow"],
    reason: str = "user_preference",
) -> str:
    """
    Change the assistant's speaking speed/pace.
    
    Use this when the user asks to speak faster or slower.
    
    Args:
        speed: The desired speaking pace - "fast", "moderate", or "slow"
        reason: Why the change is being made
    
    Returns:
        Confirmation of the change
    
    Examples:
        - User says "speak faster" → change_voice_speed(speed="fast")
        - User says "slow down" → change_voice_speed(speed="slow")
        - User says "normal speed" → change_voice_speed(speed="moderate")
    """
    manager = get_voice_manager()
    result = manager.change_pace(speed, reason)
    
    if result["success"]:
        return f"Voice changed to {result['new_voice']} ({VOICE_PROFILES[result['new_voice']]['style']}) for {speed} pace."
    else:
        return f"Failed to change voice: {result.get('error', 'Unknown error')}"


@tool
def change_voice_style(
    voice_id: str,
    reason: str = "user_preference",
) -> str:
    """
    Change the assistant's voice to a specific voice ID.
    
    Args:
        voice_id: The voice to change to. Options include:
            - Fast: Puck (Upbeat), Fenrir (Excitable)
            - Moderate: Charon (Informative), Kore (Firm), Algieba (Smooth)
            - Slow: Enceladus (Breathy), Aoede (Breezy), Gacrux (Mature)
        reason: Why the change is being made
    
    Returns:
        Confirmation of the change
    """
    manager = get_voice_manager()
    result = manager.change_voice(voice_id, reason)
    
    if result["success"]:
        return f"Voice changed from {result['old_voice']} to {result['new_voice']} ({result['voice_style']})."
    else:
        return f"Failed to change voice: {result.get('error', 'Unknown error')}"


@tool
def get_available_voices() -> str:
    """
    Get a list of all available voice options with their characteristics.
    
    Returns:
        Formatted list of available voices
    """
    result = "Available voices:\n\n"
    
    for pace in ["fast", "moderate", "slow"]:
        result += f"**{pace.upper()} PACE:**\n"
        for voice in PACE_TO_VOICES[pace]:
            profile = VOICE_PROFILES[voice]
            result += f"  - {voice}: {profile['style']} - {profile['description']}\n"
        result += "\n"
    
    return result


@tool
def get_current_voice_settings() -> str:
    """
    Get the current voice settings.
    
    Returns:
        Current voice configuration
    """
    manager = get_voice_manager()
    settings = manager.get_current_settings()
    
    return f"""Current Voice Settings:
- Voice: {settings['voice_id']}
- Style: {settings['voice_style']}
- Pace: {settings['pace']}
- Custom Instructions: {settings['custom_instructions_count']}"""


@tool
def add_speaking_instruction(
    instruction: str,
    category: str = "speaking_style",
) -> str:
    """
    Add a custom instruction to modify how the assistant speaks.
    
    Args:
        instruction: The instruction to add (e.g., "Speak in a more formal tone")
        category: Category for the instruction (speaking_style, personality, etc.)
    
    Returns:
        Confirmation of the addition
    """
    manager = get_voice_manager()
    result = manager.add_prompt_instruction(instruction, category)
    
    if result["success"]:
        return f"Added instruction: '{instruction}'. Total custom instructions: {result['total_custom_instructions']}"
    else:
        return f"Failed to add instruction: {result.get('error', 'Unknown error')}"
