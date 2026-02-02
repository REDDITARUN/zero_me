import { useAgent, AgentStatus } from '../context/AgentContext';
import ArchitecturePanel from './ArchitecturePanel';
import VoiceControlPanel from './VoiceControlPanel';
import './Dashboard.css';

// Integration status (connected to actual services)
const integrations = [
  { id: 'notion', name: 'Notion', icon: '📝', connected: true, description: 'Docs, Todos, Calendar' },
  { id: 'memory', name: 'Memory', icon: '🧠', connected: true, description: 'Redis context store' },
  { id: 'email', name: 'Email', icon: '✉️', connected: true, description: 'Resend API' },
  { id: 'wandb', name: 'Analytics', icon: '📊', connected: true, description: 'WandB tracking' },
];

const agents = [
  { id: 'casey', name: 'Casey', description: 'Voice assistant', status: 'ready' as const },
];

function StatusBadge({ status }: { status: AgentStatus }) {
  const labels: Record<AgentStatus, string> = {
    idle: 'Ready',
    connecting: 'Connecting...',
    listening: 'Listening',
    thinking: 'Thinking',
    speaking: 'Speaking',
    paused: 'Paused',
    error: 'Error',
  };
  
  return (
    <span className={`status-badge status-${status}`}>
      <span className="status-dot" />
      {labels[status]}
    </span>
  );
}

export default function Dashboard() {
  const { status, start, pause, stop, isActive } = useAgent();

  return (
    <div className="dashboard">
      {/* Draggable title bar */}
      <header className="dashboard-header drag-region">
        <div className="header-left">
          <h1 className="logo">zero me</h1>
        </div>
        <div className="header-right no-drag">
          <StatusBadge status={status} />
        </div>
      </header>

      <main className="dashboard-main">
        {/* Architecture Visualization Section */}
        <section className="section">
          <ArchitecturePanel />
        </section>

        {/* Integrations Section */}
        <section className="section">
          <h2 className="section-title">Connected Services</h2>
          <p className="section-subtitle">Active integrations powering your assistant</p>
          
          <div className="integrations-grid">
            {integrations.map((integration) => (
              <div key={integration.id} className={`integration-card ${integration.connected ? 'connected' : ''}`}>
                <span className="integration-icon">{integration.icon}</span>
                <div className="integration-info">
                  <span className="integration-name">{integration.name}</span>
                  <span className="integration-status">
                    {integration.connected ? integration.description : 'Not connected'}
                  </span>
                </div>
                <span className={`integration-badge ${integration.connected ? 'active' : ''}`}>
                  {integration.connected ? '●' : '○'}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Agent Section */}
        <section className="section">
          <h2 className="section-title">Voice Assistant</h2>
          <p className="section-subtitle">Your AI assistant powered by Gemini</p>
          
          <div className="agents-list">
            {agents.map((agent) => (
              <div key={agent.id} className="agent-card">
                <div className="agent-avatar">
                  <div className="agent-avatar-inner" />
                </div>
                <div className="agent-info">
                  <span className="agent-name">{agent.name}</span>
                  <span className="agent-description">{agent.description}</span>
                </div>
                <span className={`agent-status agent-status-${agent.status}`}>
                  {agent.status}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Voice Control Section */}
        <section className="section">
          <h2 className="section-title">Voice Settings</h2>
          <p className="section-subtitle">Control speaking pace and style</p>
          <VoiceControlPanel />
        </section>
      </main>

      {/* Controls Footer */}
      <footer className="dashboard-footer">
        <div className="controls-hint">
          <span className="hint-key">⌘⇧S</span> Start
          <span className="hint-divider">·</span>
          <span className="hint-key">⌘⇧P</span> {status === 'paused' ? 'Resume' : 'Pause'}
          <span className="hint-divider">·</span>
          <span className="hint-key">⌘⇧X</span> Stop
        </div>
        
        <div className="controls">
          <button 
            className="btn-control btn-start"
            onClick={start}
            disabled={isActive}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4 2.5v11l9-5.5-9-5.5z"/>
            </svg>
            Start
          </button>
          
          <button 
            className={`btn-control ${status === 'paused' ? 'btn-resume' : 'btn-pause'}`}
            onClick={pause}
            disabled={!isActive}
          >
            {status === 'paused' ? (
              <>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M4 2.5v11l9-5.5-9-5.5z"/>
                </svg>
                Resume
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <rect x="3" y="2" width="4" height="12" rx="1"/>
                  <rect x="9" y="2" width="4" height="12" rx="1"/>
                </svg>
                Pause
              </>
            )}
          </button>
          
          <button 
            className="btn-control btn-stop"
            onClick={stop}
            disabled={!isActive}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <rect x="2" y="2" width="12" height="12" rx="2"/>
            </svg>
            Stop
          </button>
        </div>
      </footer>
    </div>
  );
}
