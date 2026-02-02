import { useState, useEffect } from 'react';
import './VoiceControlPanel.css';

// Voice profiles with their characteristics
const VOICE_PROFILES: Record<string, { style: string; pace: string; description: string }> = {
  // Fast voices
  "Puck": { style: "Upbeat", pace: "fast", description: "Energetic and quick" },
  "Fenrir": { style: "Excitable", pace: "fast", description: "Enthusiastic and lively" },
  "Laomedeia": { style: "Upbeat", pace: "fast", description: "Cheerful and quick" },
  // Moderate voices
  "Charon": { style: "Informative", pace: "moderate", description: "Clear and steady" },
  "Kore": { style: "Firm", pace: "moderate", description: "Confident and measured" },
  "Algieba": { style: "Smooth", pace: "moderate", description: "Flowing and balanced" },
  // Slow voices
  "Enceladus": { style: "Breathy", pace: "slow", description: "Calm and relaxed" },
  "Aoede": { style: "Breezy", pace: "slow", description: "Laid-back and easy" },
  "Gacrux": { style: "Mature", pace: "slow", description: "Thoughtful and deliberate" },
};

interface VoiceSettings {
  voice_id: string;
  pace: string;
  voice_style: string;
  custom_instructions_count: number;
  recent_changes: Array<{
    timestamp: string;
    type: string;
    old_voice?: string;
    new_voice?: string;
    reason?: string;
  }>;
}

export default function VoiceControlPanel() {
  const [settings, setSettings] = useState<VoiceSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [customInstruction, setCustomInstruction] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);

  const API_BASE = 'http://localhost:8080';

  // Fetch current settings
  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_BASE}/voice/settings`);
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings(data);
      setError(null);
    } catch (err) {
      setError('Failed to load voice settings');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchSettings, 5000);
    return () => clearInterval(interval);
  }, []);

  // Change voice by pace
  const changePace = async (pace: string) => {
    try {
      const response = await fetch(`${API_BASE}/voice/pace`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pace, reason: 'ui_button_click' }),
      });
      if (!response.ok) throw new Error('Failed to change pace');
      await fetchSettings();
    } catch (err) {
      setError('Failed to change voice pace');
      console.error(err);
    }
  };

  // Change to specific voice
  const changeVoice = async (voiceId: string) => {
    try {
      const response = await fetch(`${API_BASE}/voice/change`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_id: voiceId, reason: 'ui_voice_select' }),
      });
      if (!response.ok) throw new Error('Failed to change voice');
      await fetchSettings();
    } catch (err) {
      setError('Failed to change voice');
      console.error(err);
    }
  };

  // Add custom instruction
  const addInstruction = async () => {
    if (!customInstruction.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/voice/instruction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          instruction: customInstruction, 
          category: 'speaking_style' 
        }),
      });
      if (!response.ok) throw new Error('Failed to add instruction');
      setCustomInstruction('');
      await fetchSettings();
    } catch (err) {
      setError('Failed to add instruction');
      console.error(err);
    }
  };

  // Clear all instructions
  const clearInstructions = async () => {
    try {
      const response = await fetch(`${API_BASE}/voice/instructions`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to clear instructions');
      await fetchSettings();
    } catch (err) {
      setError('Failed to clear instructions');
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="voice-control-panel loading">
        <div className="loading-spinner" />
        <span>Loading voice settings...</span>
      </div>
    );
  }

  return (
    <div className={`voice-control-panel ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="panel-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="header-content">
          <span className="panel-icon">🎤</span>
          <h3 className="panel-title">Voice Control</h3>
          {settings && (
            <span className="current-voice-badge">
              {settings.voice_id} • {settings.pace}
            </span>
          )}
        </div>
        <button className="expand-btn">
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {isExpanded && (
        <div className="panel-content">
          {error && (
            <div className="error-banner">
              {error}
              <button onClick={() => setError(null)}>×</button>
            </div>
          )}

          {/* Quick Pace Buttons */}
          <div className="pace-controls">
            <span className="control-label">Speaking Pace:</span>
            <div className="pace-buttons">
              <button
                className={`pace-btn ${settings?.pace === 'slow' ? 'active' : ''}`}
                onClick={() => changePace('slow')}
                title="Calm, relaxed speech"
              >
                🐢 Slow
              </button>
              <button
                className={`pace-btn ${settings?.pace === 'moderate' ? 'active' : ''}`}
                onClick={() => changePace('moderate')}
                title="Balanced, clear speech"
              >
                ⚖️ Moderate
              </button>
              <button
                className={`pace-btn ${settings?.pace === 'fast' ? 'active' : ''}`}
                onClick={() => changePace('fast')}
                title="Energetic, quick speech"
              >
                🐇 Fast
              </button>
            </div>
          </div>

          {/* Voice Selection */}
          <div className="voice-selection">
            <span className="control-label">Voice Style:</span>
            <div className="voice-grid">
              {Object.entries(VOICE_PROFILES).map(([voiceId, profile]) => (
                <button
                  key={voiceId}
                  className={`voice-btn ${settings?.voice_id === voiceId ? 'active' : ''} pace-${profile.pace}`}
                  onClick={() => changeVoice(voiceId)}
                  title={profile.description}
                >
                  <span className="voice-name">{voiceId}</span>
                  <span className="voice-style">{profile.style}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Instructions */}
          <div className="custom-instructions">
            <span className="control-label">
              Custom Instructions ({settings?.custom_instructions_count || 0}):
            </span>
            <div className="instruction-input">
              <input
                type="text"
                placeholder="e.g., Speak in a more formal tone"
                value={customInstruction}
                onChange={(e) => setCustomInstruction(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addInstruction()}
              />
              <button 
                className="add-btn"
                onClick={addInstruction}
                disabled={!customInstruction.trim()}
              >
                Add
              </button>
            </div>
            {(settings?.custom_instructions_count || 0) > 0 && (
              <button className="clear-btn" onClick={clearInstructions}>
                Clear All Instructions
              </button>
            )}
          </div>

          {/* Recent Changes */}
          {settings?.recent_changes && settings.recent_changes.length > 0 && (
            <div className="recent-changes">
              <span className="control-label">Recent Changes:</span>
              <ul className="changes-list">
                {settings.recent_changes.slice(-3).reverse().map((change, idx) => (
                  <li key={idx} className="change-item">
                    {change.type === 'voice_change' ? (
                      <span>
                        <span className="change-icon">🔊</span>
                        {change.old_voice} → {change.new_voice}
                      </span>
                    ) : (
                      <span>
                        <span className="change-icon">📝</span>
                        Instruction added
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Current Settings Display */}
          <div className="current-settings">
            <div className="setting-row">
              <span className="setting-label">Current Voice:</span>
              <span className="setting-value">{settings?.voice_id || 'Unknown'}</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">Style:</span>
              <span className="setting-value">{settings?.voice_style || 'Unknown'}</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">Pace:</span>
              <span className="setting-value pace-indicator">
                {settings?.pace === 'fast' && '🐇 Fast'}
                {settings?.pace === 'moderate' && '⚖️ Moderate'}
                {settings?.pace === 'slow' && '🐢 Slow'}
              </span>
            </div>
          </div>

          <div className="panel-footer">
            <span className="footer-note">
              💡 Say "speak faster" or "slow down" during conversation to change voice
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
