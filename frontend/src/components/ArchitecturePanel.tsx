import { useState, useEffect, useRef, useCallback } from 'react';
import './ArchitecturePanel.css';

// Types for architecture data
interface ArchNode {
  id: string;
  label: string;
  type: 'agent' | 'service' | 'integration';
  x: number;
  y: number;
}

interface ArchEdge {
  from: string;
  to: string;
  label: string;
}

interface ToolCall {
  id: string;
  tool_name: string;
  node_from: string;
  node_to: string;
  status: 'started' | 'in_progress' | 'success' | 'error';
  params: Record<string, any>;
  result?: string;
  duration_ms?: number;
}

interface SessionStats {
  session_id: string;
  duration_seconds: number;
  tool_calls_total: number;
  tool_calls_success: number;
  tool_calls_error: number;
  tasks_delegated: number;
  memories_accessed: number;
  questions_asked: number;
  active_node?: string;
  active_tool?: string;
}

interface ArchitectureData {
  nodes: ArchNode[];
  edges: ArchEdge[];
}

const STATUS_ENDPOINT = import.meta.env.VITE_STATUS_ENDPOINT || 'http://localhost:8080/status';

// Default architecture for when backend isn't connected
// All coordinates within 0-600 range with proper spacing
const DEFAULT_ARCHITECTURE: ArchitectureData = {
  nodes: [
    // Top level - Voice Agent (centered at 300)
    { id: 'voice_agent', label: 'Casey (Voice)', type: 'agent', x: 300, y: 40 },
    
    // Second level - Memory and Main Dispatcher
    { id: 'memory', label: 'Memory', type: 'service', x: 120, y: 110 },
    { id: 'main_agent', label: 'Dispatcher', type: 'agent', x: 300, y: 110 },
    
    // Third level - Sub Agents (evenly spaced from 80 to 520)
    { id: 'doc_agent', label: 'Docs', type: 'agent', x: 100, y: 190 },
    { id: 'todo_agent', label: 'Todos', type: 'agent', x: 233, y: 190 },
    { id: 'email_agent', label: 'Email', type: 'agent', x: 366, y: 190 },
    { id: 'calendar_agent', label: 'Calendar', type: 'agent', x: 500, y: 190 },
    
    // Bottom level - Integrations
    { id: 'personality_enhancer', label: 'Personality', type: 'agent', x: 60, y: 270 },
    { id: 'notion', label: 'Notion', type: 'integration', x: 200, y: 270 },
    { id: 'email_service', label: 'Resend', type: 'integration', x: 366, y: 270 },
    { id: 'wandb', label: 'WandB', type: 'integration', x: 520, y: 270 },
  ],
  edges: [
    // Voice agent connections
    { from: 'voice_agent', to: 'main_agent', label: 'delegate' },
    { from: 'voice_agent', to: 'memory', label: 'remember' },
    
    // Dispatcher to sub-agents
    { from: 'main_agent', to: 'doc_agent', label: 'docs' },
    { from: 'main_agent', to: 'todo_agent', label: 'todos' },
    { from: 'main_agent', to: 'email_agent', label: 'email' },
    { from: 'main_agent', to: 'calendar_agent', label: 'calendar' },
    
    // Sub-agents to integrations
    { from: 'doc_agent', to: 'notion', label: 'API' },
    { from: 'todo_agent', to: 'notion', label: 'API' },
    { from: 'calendar_agent', to: 'notion', label: 'API' },
    { from: 'email_agent', to: 'email_service', label: 'send' },
    
    // Personality enhancer connections
    { from: 'personality_enhancer', to: 'memory', label: 'analyze' },
    { from: 'personality_enhancer', to: 'wandb', label: 'log' },
  ]
};

export default function ArchitecturePanel() {
  const [architecture, setArchitecture] = useState<ArchitectureData>(DEFAULT_ARCHITECTURE);
  const [stats, setStats] = useState<SessionStats | null>(null);
  const [recentCalls, setRecentCalls] = useState<ToolCall[]>([]);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [activeEdge, setActiveEdge] = useState<{from: string; to: string} | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [pulsingNode, setPulsingNode] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);

  // Fetch initial data via REST
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [archRes, statsRes, recentRes] = await Promise.all([
          fetch(`${STATUS_ENDPOINT}/architecture`).catch(() => null),
          fetch(`${STATUS_ENDPOINT}/stats`).catch(() => null),
          fetch(`${STATUS_ENDPOINT}/recent`).catch(() => null),
        ]);

        if (archRes?.ok) {
          const data = await archRes.json();
          if (data.nodes) setArchitecture(data);
        }
        if (statsRes?.ok) {
          const data = await statsRes.json();
          if (data.session_id) setStats(data);
        }
        if (recentRes?.ok) {
          const data = await recentRes.json();
          if (Array.isArray(data)) setRecentCalls(data);
        }
      } catch (e) {
        console.log('Using default architecture (backend not available)');
      }
    };

    fetchInitialData();
  }, []);

  // Connect to SSE stream
  useEffect(() => {
    const connectToStream = () => {
      try {
        const eventSource = new EventSource(`${STATUS_ENDPOINT}/stream`);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          console.log('📡 Connected to status stream');
          setIsConnected(true);
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleStatusEvent(data);
          } catch (e) {
            console.error('Failed to parse status event:', e);
          }
        };

        eventSource.onerror = () => {
          console.log('📡 Status stream disconnected, reconnecting...');
          setIsConnected(false);
          eventSource.close();
          setTimeout(connectToStream, 5000);
        };
      } catch (e) {
        console.log('SSE not available, using polling');
        setIsConnected(false);
      }
    };

    connectToStream();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Handle incoming status events
  const handleStatusEvent = useCallback((event: any) => {
    switch (event.type) {
      case 'init':
        if (event.data.architecture) {
          setArchitecture(event.data.architecture);
        }
        if (event.data.stats) {
          setStats(event.data.stats);
        }
        if (event.data.recent_calls) {
          setRecentCalls(event.data.recent_calls);
        }
        break;

      case 'tool_call_start':
        setActiveNode(event.data.node_to);
        setActiveEdge({ from: event.data.node_from, to: event.data.node_to });
        setPulsingNode(event.data.node_to);
        setRecentCalls(prev => [...prev.slice(-9), event.data]);
        // Update stats incrementally
        setStats(prev => prev ? {
          ...prev,
          tool_calls_total: prev.tool_calls_total + 1,
          active_node: event.data.node_to,
          active_tool: event.data.tool_name,
        } : null);
        break;

      case 'tool_call_complete':
        // Keep glow for a moment after completion
        setTimeout(() => {
          setActiveNode(null);
          setActiveEdge(null);
          setPulsingNode(null);
        }, 500);
        setRecentCalls(prev => 
          prev.map(call => call.id === event.data.id ? event.data : call)
        );
        // Update stats
        setStats(prev => prev ? {
          ...prev,
          tool_calls_success: event.data.status === 'success' ? prev.tool_calls_success + 1 : prev.tool_calls_success,
          tool_calls_error: event.data.status === 'error' ? prev.tool_calls_error + 1 : prev.tool_calls_error,
          active_node: undefined,
          active_tool: undefined,
        } : null);
        break;

      case 'session_start':
        setStats(event.data);
        setRecentCalls([]);
        break;

      case 'session_end':
        setStats(event.data);
        setActiveNode(null);
        setActiveEdge(null);
        setPulsingNode(null);
        break;

      case 'active_node':
        setActiveNode(event.data.node);
        setPulsingNode(event.data.node);
        break;

      default:
        // Update stats if present
        if (event.data?.stats) {
          setStats(event.data.stats);
        }
    }
  }, []);

  // Animation frame for pulsing effect
  const [animationPhase, setAnimationPhase] = useState(0);

  useEffect(() => {
    if (pulsingNode) {
      const animate = () => {
        setAnimationPhase(prev => (prev + 0.1) % (Math.PI * 2));
        animationRef.current = requestAnimationFrame(animate);
      };
      animationRef.current = requestAnimationFrame(animate);
    } else {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [pulsingNode]);

  // Draw the architecture network
  useEffect(() => {
    if (!canvasRef.current || !architecture) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to match parent
    const rect = canvas.parentElement?.getBoundingClientRect();
    if (rect) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Scale factor for responsive sizing with proper margins
    const paddingX = 80; // Horizontal padding from edges
    const paddingY = 40; // Vertical padding from edges
    const contentWidth = 600; // Virtual content width (max X in nodes is ~580)
    const contentHeight = 340; // Virtual content height (max Y in nodes is ~290 + label space)
    
    const availableWidth = canvas.width - paddingX * 2;
    const availableHeight = canvas.height - paddingY * 2;
    
    const scaleX = availableWidth / contentWidth;
    const scaleY = availableHeight / contentHeight;
    const scale = Math.min(scaleX, scaleY); // Use smaller scale to fit both dimensions
    
    // Center the content
    const offsetX = paddingX + (availableWidth - contentWidth * scale) / 2;
    const offsetY = paddingY;

    // Draw edges first
    architecture.edges.forEach(edge => {
      const fromNode = architecture.nodes.find(n => n.id === edge.from);
      const toNode = architecture.nodes.find(n => n.id === edge.to);
      if (!fromNode || !toNode) return;

      const x1 = fromNode.x * scale + offsetX;
      const y1 = fromNode.y * scale + offsetY;
      const x2 = toNode.x * scale + offsetX;
      const y2 = toNode.y * scale + offsetY;

      const isActiveEdge = activeEdge?.from === edge.from && activeEdge?.to === edge.to;

      // Draw base edge - thicker and more visible
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = isActiveEdge ? '#7ed6a5' : 'rgba(120, 120, 120, 0.35)';
      ctx.lineWidth = isActiveEdge ? 4 : 2;
      ctx.stroke();
      
      // Draw arrow at end
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const arrowSize = Math.max(6, 7 * scale);
      const nodeRadius = Math.max(22, 26 * scale);
      const arrowX = x2 - (nodeRadius + 5) * Math.cos(angle);
      const arrowY = y2 - (nodeRadius + 5) * Math.sin(angle);
      
      ctx.beginPath();
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - arrowSize * Math.cos(angle - Math.PI / 6),
        arrowY - arrowSize * Math.sin(angle - Math.PI / 6)
      );
      ctx.lineTo(
        arrowX - arrowSize * Math.cos(angle + Math.PI / 6),
        arrowY - arrowSize * Math.sin(angle + Math.PI / 6)
      );
      ctx.closePath();
      ctx.fillStyle = isActiveEdge ? '#7ed6a5' : 'rgba(120, 120, 120, 0.5)';
      ctx.fill();

      // Draw animated glow for active edge
      if (isActiveEdge) {
        const glowIntensity = 0.3 + Math.sin(animationPhase) * 0.2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = `rgba(126, 214, 165, ${glowIntensity})`;
        ctx.lineWidth = 10 + Math.sin(animationPhase) * 3;
        ctx.stroke();
        
        // Draw animated particle along edge
        const progress = (animationPhase / (Math.PI * 2));
        const px = x1 + (x2 - x1) * progress;
        const py = y1 + (y2 - y1) * progress;
        ctx.beginPath();
        ctx.arc(px, py, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#7ed6a5';
        ctx.fill();
      }
    });

    // Draw nodes
    architecture.nodes.forEach(node => {
      const x = node.x * scale + offsetX;
      const y = node.y * scale + offsetY;
      const isActive = activeNode === node.id;
      const isPulsing = pulsingNode === node.id;
      const radius = Math.max(22, 26 * scale); // Reasonable node size

      // Animated glow effect for pulsing node
      if (isPulsing) {
        const glowSize = radius + 8 + Math.sin(animationPhase) * 4;
        ctx.beginPath();
        ctx.arc(x, y, glowSize, 0, Math.PI * 2);
        const gradient = ctx.createRadialGradient(x, y, radius, x, y, glowSize + 8);
        const glowOpacity = 0.5 + Math.sin(animationPhase) * 0.2;
        gradient.addColorStop(0, `rgba(126, 214, 165, ${glowOpacity})`);
        gradient.addColorStop(1, 'rgba(126, 214, 165, 0)');
        ctx.fillStyle = gradient;
        ctx.fill();
      } else if (isActive) {
        // Static glow for active but not pulsing
        ctx.beginPath();
        ctx.arc(x, y, radius + 8, 0, Math.PI * 2);
        const gradient = ctx.createRadialGradient(x, y, radius, x, y, radius + 12);
        gradient.addColorStop(0, 'rgba(126, 214, 165, 0.4)');
        gradient.addColorStop(1, 'rgba(126, 214, 165, 0)');
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      
      const colors: Record<string, string> = {
        agent: isActive || isPulsing ? '#7ed6a5' : '#f5e6d3',
        service: isActive || isPulsing ? '#a78bfa' : '#e8e1f4',
        integration: isActive || isPulsing ? '#f9a875' : '#fce4d4',
      };
      ctx.fillStyle = colors[node.type] || '#f5f5f5';
      ctx.fill();
      
      ctx.strokeStyle = isActive || isPulsing ? '#4a9c6d' : 'rgba(0,0,0,0.1)';
      ctx.lineWidth = isActive || isPulsing ? 2 : 1;
      ctx.stroke();

      // Node label - below node
      ctx.fillStyle = isActive || isPulsing ? '#2d5d3e' : '#444';
      ctx.font = `600 ${Math.max(10, 11 * scale)}px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      
      const label = node.label.length > 12 ? node.label.slice(0, 10) + '...' : node.label;
      ctx.fillText(label, x, y + radius + 6);
      
      // Draw icon inside node based on type
      const iconSize = Math.max(14, 16 * scale);
      ctx.font = `${iconSize}px Arial`;
      ctx.textBaseline = 'middle';
      
      const icons: Record<string, string> = {
        agent: '🤖',
        service: '💾',
        integration: '🔗',
      };
      if (node.id === 'voice_agent') ctx.fillText('🎙️', x, y);
      else if (node.id === 'memory') ctx.fillText('🧠', x, y);
      else if (node.id === 'notion') ctx.fillText('📝', x, y);
      else if (node.id === 'email_service') ctx.fillText('✉️', x, y);
      else if (node.id === 'wandb') ctx.fillText('📊', x, y);
      else if (node.id === 'personality_enhancer') ctx.fillText('✨', x, y);
      else ctx.fillText(icons[node.type] || '⚡', x, y);
    });
  }, [architecture, activeNode, activeEdge, pulsingNode, animationPhase]);

  // Format duration
  const formatDuration = (ms?: number) => {
    if (!ms) return '-';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  // Demo simulation for testing UI
  const simulateToolCall = useCallback(() => {
    const demoFlows = [
      { from: 'voice_agent', to: 'main_agent', tool: 'delegate_task' },
      { from: 'main_agent', to: 'todo_agent', tool: 'todo_operation' },
      { from: 'todo_agent', to: 'notion', tool: 'add_todo' },
      { from: 'voice_agent', to: 'memory', tool: 'remember_info' },
      { from: 'main_agent', to: 'email_agent', tool: 'send_email' },
      { from: 'email_agent', to: 'email_service', tool: 'resend_api' },
    ];
    
    const flow = demoFlows[Math.floor(Math.random() * demoFlows.length)];
    const callId = `demo_${Date.now()}`;
    
    // Simulate start
    setActiveNode(flow.to);
    setActiveEdge({ from: flow.from, to: flow.to });
    setPulsingNode(flow.to);
    setRecentCalls(prev => [...prev.slice(-9), {
      id: callId,
      tool_name: flow.tool,
      node_from: flow.from,
      node_to: flow.to,
      status: 'started',
      params: {},
    }]);
    setStats(prev => prev ? { ...prev, tool_calls_total: prev.tool_calls_total + 1 } : {
      session_id: 'demo',
      duration_seconds: 0,
      tool_calls_total: 1,
      tool_calls_success: 0,
      tool_calls_error: 0,
      tasks_delegated: 1,
      memories_accessed: 0,
      questions_asked: 0,
    });
    
    // Simulate complete after delay
    setTimeout(() => {
      setActiveNode(null);
      setActiveEdge(null);
      setPulsingNode(null);
      setRecentCalls(prev => prev.map(call => 
        call.id === callId 
          ? { ...call, status: 'success' as const, duration_ms: 150 + Math.random() * 300 }
          : call
      ));
      setStats(prev => prev ? { ...prev, tool_calls_success: prev.tool_calls_success + 1 } : null);
    }, 1500);
  }, []);

  return (
    <div className="architecture-panel">
      {/* Header */}
      <div className="arch-header">
        <h2 className="arch-title">System Architecture</h2>
        <div className="arch-header-right">
          <button className="demo-btn" onClick={simulateToolCall} title="Test visualization">
            Test
          </button>
          <div className="arch-status">
            <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
            {isConnected ? 'Live' : 'Offline'}
          </div>
        </div>
      </div>

      {/* Network Visualization */}
      <div className="arch-network">
        <canvas ref={canvasRef} className="arch-canvas" />
        {/* Legend */}
        <div className="arch-legend">
          <div className="legend-item">
            <span className="legend-dot agent"></span>
            <span>Agent</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot service"></span>
            <span>Service</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot integration"></span>
            <span>Integration</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot active"></span>
            <span>Active</span>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="arch-stats">
          <div className="stat-item">
            <span className="stat-value">{stats.tool_calls_total}</span>
            <span className="stat-label">Tool Calls</span>
          </div>
          <div className="stat-item">
            <span className="stat-value stat-success">{stats.tool_calls_success}</span>
            <span className="stat-label">Success</span>
          </div>
          <div className="stat-item">
            <span className="stat-value stat-error">{stats.tool_calls_error}</span>
            <span className="stat-label">Errors</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.tasks_delegated}</span>
            <span className="stat-label">Tasks</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.memories_accessed}</span>
            <span className="stat-label">Memory</span>
          </div>
        </div>
      )}

      {/* Recent Tool Calls */}
      <div className="arch-calls">
        <h3 className="calls-title">Recent Activity</h3>
        <div className="calls-list">
          {recentCalls.slice(-5).reverse().map((call) => (
            <div key={call.id} className={`call-item call-${call.status}`}>
              <div className="call-icon">
                {call.status === 'started' && '⏳'}
                {call.status === 'success' && '✅'}
                {call.status === 'error' && '❌'}
              </div>
              <div className="call-info">
                <span className="call-name">{call.tool_name}</span>
                <span className="call-route">{call.node_from} → {call.node_to}</span>
              </div>
              <div className="call-duration">
                {formatDuration(call.duration_ms)}
              </div>
            </div>
          ))}
          {recentCalls.length === 0 && (
            <div className="calls-empty">No activity yet. Start a conversation!</div>
          )}
        </div>
      </div>
    </div>
  );
}
