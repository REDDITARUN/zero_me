import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { AgentStatus } from '../context/AgentContext';
import './Blob.css';

interface BlobProps {
  status: AgentStatus;
  volume?: number;
  size?: number;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  color: { r: number; g: number; b: number };
  life: number;
}

interface Ripple {
  id: number;
  progress: number;
  intensity: number;
}

interface ColorSet {
  primary: { r: number; g: number; b: number };
  secondary: { r: number; g: number; b: number };
  gradient: [string, string, string];
}

// Color presets for each state
const COLOR_PRESETS: Record<string, ColorSet> = {
  idle: {
    primary: { r: 245, g: 168, b: 154 },     // Warm coral
    secondary: { r: 252, g: 213, b: 207 },
    gradient: ['#fcd5cf', '#f5a89a', '#e8826f'],
  },
  connecting: {
    primary: { r: 245, g: 213, b: 168 },     // Warm amber
    secondary: { r: 250, g: 230, b: 200 },
    gradient: ['#fae6c8', '#f5d5a8', '#f0c88a'],
  },
  listening: {
    primary: { r: 126, g: 214, b: 165 },     // Warm green
    secondary: { r: 168, g: 230, b: 195 },
    gradient: ['#a8e6c3', '#7ed6a5', '#5cc88a'],
  },
  thinking: {
    primary: { r: 180, g: 170, b: 245 },     // Light purple
    secondary: { r: 210, g: 200, b: 255 },
    gradient: ['#d2ccff', '#b4aaf5', '#9a8ce8'],
  },
  speaking: {
    primary: { r: 168, g: 130, b: 245 },     // Vibrant purple
    secondary: { r: 198, g: 170, b: 255 },
    gradient: ['#c6aaff', '#a882f5', '#8a5ce8'],
  },
  paused: {
    primary: { r: 200, g: 200, b: 200 },     // Gray
    secondary: { r: 230, g: 230, b: 230 },
    gradient: ['#e6e6e6', '#c8c8c8', '#aaaaaa'],
  },
  error: {
    primary: { r: 245, g: 130, b: 130 },     // Red
    secondary: { r: 255, g: 180, b: 180 },
    gradient: ['#ffb4b4', '#f58282', '#e85c5c'],
  },
};

// Smooth color interpolation
function lerpColor(a: { r: number; g: number; b: number }, b: { r: number; g: number; b: number }, t: number) {
  return {
    r: Math.round(a.r + (b.r - a.r) * t),
    g: Math.round(a.g + (b.g - a.g) * t),
    b: Math.round(a.b + (b.b - a.b) * t),
  };
}

function lerpGradient(a: [string, string, string], b: [string, string, string], t: number): [string, string, string] {
  const parseHex = (hex: string) => ({
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  });
  const toHex = (c: { r: number; g: number; b: number }) =>
    `#${c.r.toString(16).padStart(2, '0')}${c.g.toString(16).padStart(2, '0')}${c.b.toString(16).padStart(2, '0')}`;
  
  return [
    toHex(lerpColor(parseHex(a[0]), parseHex(b[0]), t)),
    toHex(lerpColor(parseHex(a[1]), parseHex(b[1]), t)),
    toHex(lerpColor(parseHex(a[2]), parseHex(b[2]), t)),
  ];
}

export default function Blob({ status, volume = 0, size = 120 }: BlobProps) {
  // Animated color state with smooth transitions
  const [currentColors, setCurrentColors] = useState<ColorSet>(COLOR_PRESETS.idle);
  const [targetColors, setTargetColors] = useState<ColorSet>(COLOR_PRESETS.idle);
  const [colorTransition, setColorTransition] = useState(1); // 0-1, 1 = complete
  const [transitionBurst, setTransitionBurst] = useState(0); // Burst effect on state change
  
  // Animation state
  const [pulse, setPulse] = useState(0);
  const [gradPhase, setGradPhase] = useState(0);
  const [eyeLook, setEyeLook] = useState({ x: 0, y: 0 });
  const [eyeOpen, setEyeOpen] = useState(1);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [ripples, setRipples] = useState<Ripple[]>([]);
  
  const requestRef = useRef<number>();
  const blinkTimeout = useRef<NodeJS.Timeout | null>(null);
  const lookTimeout = useRef<NodeJS.Timeout | null>(null);
  const particleIdRef = useRef(0);
  const rippleIdRef = useRef(0);
  const prevStatusRef = useRef(status);

  // Trigger color transition when status changes
  useEffect(() => {
    if (status !== prevStatusRef.current) {
      const newTarget = COLOR_PRESETS[status] || COLOR_PRESETS.idle;
      setTargetColors(newTarget);
      setColorTransition(0);
      setTransitionBurst(1); // Trigger burst effect
      prevStatusRef.current = status;
      
      // Spawn burst particles on state change
      const burstParticles: Particle[] = [];
      for (let i = 0; i < 12; i++) {
        const angle = (i / 12) * Math.PI * 2;
        const speed = 1.5 + Math.random() * 2;
        burstParticles.push({
          id: particleIdRef.current++,
          x: size / 2,
          y: size / 2,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          size: 3 + Math.random() * 5,
          opacity: 0.8,
          color: newTarget.primary,
          life: 1,
        });
      }
      setParticles(prev => [...prev, ...burstParticles]);
    }
  }, [status, size]);

  // Interpolated colors for rendering
  const displayColors = useMemo(() => {
    const t = colorTransition;
    return {
      primary: lerpColor(currentColors.primary, targetColors.primary, t),
      secondary: lerpColor(currentColors.secondary, targetColors.secondary, t),
      gradient: lerpGradient(currentColors.gradient, targetColors.gradient, t),
    };
  }, [currentColors, targetColors, colorTransition]);

  const isActive = status === 'listening' || status === 'speaking' || status === 'thinking';

  // Spawn particles when speaking or listening with audio
  useEffect(() => {
    if ((status === 'speaking' && volume > 0.02) || (status === 'listening' && volume > 0.05)) {
      const count = Math.floor(volume * 4) + 1;
      const newParticles: Particle[] = [];
      
      for (let i = 0; i < count; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = 0.5 + Math.random() * 1.5 + volume * 2;
        newParticles.push({
          id: particleIdRef.current++,
          x: size / 2,
          y: size / 2,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          size: 2 + Math.random() * 4 + volume * 3,
          opacity: 0.6 + Math.random() * 0.4,
          color: displayColors.primary,
          life: 1,
        });
      }
      
      setParticles(prev => [...prev.slice(-40), ...newParticles]);
    }
  }, [volume, status, size, displayColors.primary]);

  // Spawn ripples for audio feedback
  useEffect(() => {
    if (isActive && volume > 0.03) {
      const intensity = Math.min(volume * 2.5, 1);
      setRipples(prev => [...prev.slice(-5), {
        id: rippleIdRef.current++,
        progress: 0,
        intensity,
      }]);
    }
  }, [volume, isActive]);

  // Main animation loop
  useEffect(() => {
    let last = Date.now();
    
    const animate = () => {
      const now = Date.now();
      const dt = (now - last) / 1000;
      last = now;

      // Color transition (smooth over ~400ms)
      setColorTransition(prev => {
        if (prev < 1) {
          const newVal = prev + dt * 2.5; // ~400ms transition
          if (newVal >= 1) {
            setCurrentColors(targetColors);
            return 1;
          }
          return newVal;
        }
        return 1;
      });

      // Burst effect decay
      setTransitionBurst(prev => Math.max(0, prev - dt * 3));

      // Pulse speed based on state
      const pulseSpeed = status === 'speaking' ? 3 + volume * 4 
        : status === 'listening' ? 2 
        : status === 'thinking' ? 2.5 
        : 1.2;
      
      setPulse(prev => prev + dt * pulseSpeed);
      setGradPhase(prev => prev + dt * (0.2 + (isActive ? 0.15 : 0) + volume * 0.3));
      
      // Update particles
      setParticles(prev => prev
        .map(p => ({
          ...p,
          x: p.x + p.vx,
          y: p.y + p.vy,
          vx: p.vx * 0.98,
          vy: p.vy * 0.98,
          life: p.life - dt * 0.7,
          opacity: p.opacity * (0.97 - dt * 0.3),
        }))
        .filter(p => p.life > 0 && p.opacity > 0.03)
      );
      
      // Update ripples
      setRipples(prev => prev
        .map(r => ({ ...r, progress: r.progress + dt * 1.8 }))
        .filter(r => r.progress < 1)
      );

      requestRef.current = requestAnimationFrame(animate);
    };
    
    requestRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(requestRef.current!);
  }, [status, volume, isActive, targetColors]);

  // Eye blinking
  useEffect(() => {
    const blink = () => {
      setEyeOpen(0);
      setTimeout(() => setEyeOpen(1), 100 + Math.random() * 60);
      blinkTimeout.current = setTimeout(blink, 2000 + Math.random() * 2000);
    };
    blinkTimeout.current = setTimeout(blink, 1500 + Math.random() * 1500);
    return () => { if (blinkTimeout.current) clearTimeout(blinkTimeout.current); };
  }, []);

  // Eye looking around
  useEffect(() => {
    const look = () => {
      const dirs = [
        { x: 0, y: 0 }, { x: -1, y: 0 }, { x: 1, y: 0 },
        { x: 0, y: 1 }, { x: 0, y: -1 }, { x: -0.7, y: 0.7 },
      ];
      setEyeLook(dirs[Math.floor(Math.random() * dirs.length)]);
      lookTimeout.current = setTimeout(look, 1500 + Math.random() * 2000);
    };
    lookTimeout.current = setTimeout(look, 1000);
    return () => { if (lookTimeout.current) clearTimeout(lookTimeout.current); };
  }, []);

  // Geometry
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.35;
  
  // Dynamic scaling with more reaction to speaking
  const speakingBoost = status === 'speaking' ? volume * 0.15 : 0;
  const burstScale = transitionBurst * 0.1;
  const pulseStrength = 0.04 + 0.06 * Math.abs(Math.sin(pulse * 0.7)) + volume * 0.1 + speakingBoost + burstScale;
  const scale = 1 + pulseStrength;

  // Gradient animation - faster when speaking
  const gradCx = 55 + Math.sin(gradPhase) * 15 + (status === 'speaking' ? Math.sin(gradPhase * 3) * 5 : 0);
  const gradCy = 35 + Math.cos(gradPhase * 1.3) * 12 + (status === 'speaking' ? Math.cos(gradPhase * 3) * 5 : 0);

  // Eyes
  const eyeW = size * 0.07;
  const eyeHopen = size * 0.14;
  const eyeH = eyeOpen * eyeHopen + (1 - eyeOpen) * (size * 0.02);
  const eyeY = cy - size * 0.01 + eyeLook.y * size * 0.025;
  const leftEyeX = cx - size * 0.07 + eyeLook.x * size * 0.025;
  const rightEyeX = cx + size * 0.07 + eyeLook.x * size * 0.025;
  const eyeRadius = size * 0.035;

  // Unique gradient IDs
  const instanceId = useMemo(() => Math.random().toString(36).slice(2), []);
  const gradientId = `blob-grad-${instanceId}`;
  const glowId = `blob-glow-${instanceId}`;
  const overlayId = `blob-overlay-${instanceId}`;

  // RGB string helpers
  const rgb = (c: { r: number; g: number; b: number }) => `rgb(${c.r}, ${c.g}, ${c.b})`;
  const rgba = (c: { r: number; g: number; b: number }, a: number) => `rgba(${c.r}, ${c.g}, ${c.b}, ${a})`;

  return (
    <div className="blob-container" style={{ width: size + 60, height: size + 60 }}>
      {/* Floating particles */}
      <svg 
        className="blob-particles"
        viewBox={`0 0 ${size + 60} ${size + 60}`}
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      >
        {particles.map(p => (
          <circle
            key={p.id}
            cx={p.x + 30}
            cy={p.y + 30}
            r={p.size}
            fill={rgba(p.color, p.opacity)}
            style={{ filter: 'blur(1px)' }}
          />
        ))}
      </svg>

      {/* Outer glow and ripples */}
      <svg
        className="blob-glow"
        viewBox={`0 0 ${size + 60} ${size + 60}`}
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      >
        <defs>
          <radialGradient id={glowId}>
            <stop offset="0%" stopColor={rgba(displayColors.primary, 0.5)} />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          <filter id={`${glowId}-blur`}>
            <feGaussianBlur stdDeviation={size * 0.08} />
          </filter>
        </defs>
        
        {/* Ambient glow - larger when speaking */}
        <circle
          cx={cx + 30}
          cy={cy + 30}
          r={r * (1.8 + (status === 'speaking' ? 0.3 + volume * 0.5 : 0) + transitionBurst * 0.5)}
          fill={`url(#${glowId})`}
          opacity={0.6 + volume * 0.4 + transitionBurst * 0.3}
          style={{ filter: `url(#${glowId}-blur)` }}
        />
        
        {/* Ripples */}
        {ripples.map(ripple => (
          <circle
            key={ripple.id}
            cx={cx + 30}
            cy={cy + 30}
            r={r + size * 0.1 + ripple.progress * size * 0.35}
            fill="none"
            stroke={rgba(displayColors.primary, ripple.intensity * (1 - ripple.progress) * 0.6)}
            strokeWidth={3 * ripple.intensity * (1 - ripple.progress)}
          />
        ))}
        
        {/* Breathing ring */}
        {isActive && (
          <circle
            cx={cx + 30}
            cy={cy + 30}
            r={r + size * 0.1 + Math.sin(pulse * 0.5) * size * 0.04}
            fill="none"
            stroke={rgba(displayColors.primary, 0.35)}
            strokeWidth={2}
          />
        )}

        {/* Second ring when speaking */}
        {status === 'speaking' && (
          <circle
            cx={cx + 30}
            cy={cy + 30}
            r={r + size * 0.18 + Math.sin(pulse * 0.7 + 1) * size * 0.03}
            fill="none"
            stroke={rgba(displayColors.secondary, 0.25)}
            strokeWidth={1.5}
          />
        )}
      </svg>

      {/* Main blob sphere */}
      <svg
        className="blob-main"
        viewBox={`0 0 ${size + 60} ${size + 60}`}
        style={{ position: 'absolute', inset: 0 }}
      >
        <defs>
          {/* Main gradient - updates with interpolated colors */}
          <radialGradient id={gradientId} cx={`${gradCx}%`} cy={`${gradCy}%`} r="70%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="25%" stopColor={displayColors.gradient[0]} />
            <stop offset="60%" stopColor={displayColors.gradient[1]} />
            <stop offset="100%" stopColor={displayColors.gradient[2]} />
          </radialGradient>
          
          {/* Glass overlay */}
          <radialGradient id={overlayId} cx="35%" cy="25%" r="80%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.7)" />
            <stop offset="40%" stopColor="rgba(255,255,255,0.2)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          
          {/* Shadow */}
          <filter id={`${gradientId}-shadow`} x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor={displayColors.gradient[2]} floodOpacity="0.25"/>
          </filter>
        </defs>

        {/* Shadow on ground */}
        <ellipse
          cx={cx + 30}
          cy={cy + 30 + r * 1.15}
          rx={r * 0.7 * scale}
          ry={r * 0.15}
          fill="rgba(0,0,0,0.1)"
          style={{ filter: 'blur(6px)' }}
        />

        {/* Main sphere body */}
        <circle
          cx={cx + 30}
          cy={cy + 30}
          r={r * scale}
          fill={`url(#${gradientId})`}
          style={{ filter: `url(#${gradientId}-shadow)` }}
        />
        
        {/* Glass overlay for 3D depth */}
        <circle
          cx={cx + 30}
          cy={cy + 30}
          r={r * scale}
          fill={`url(#${overlayId})`}
        />
        
        {/* Inner highlight reflection */}
        <ellipse
          cx={cx + 30 - size * 0.03}
          cy={cy + 30 - size * 0.04}
          rx={r * scale * 0.4}
          ry={r * scale * 0.25}
          fill="rgba(255,255,255,0.5)"
        />

        {/* Eyes */}
        <g className="blob-eyes">
          {/* Eye shadows */}
          <rect
            x={leftEyeX + 30 - eyeW / 2 + 1}
            y={eyeY + 30 - eyeH / 2 + 1}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="rgba(0,0,0,0.1)"
          />
          <rect
            x={rightEyeX + 30 - eyeW / 2 + 1}
            y={eyeY + 30 - eyeH / 2 + 1}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="rgba(0,0,0,0.1)"
          />
          
          {/* Eyes */}
          <rect
            x={leftEyeX + 30 - eyeW / 2}
            y={eyeY + 30 - eyeH / 2}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="#ffffff"
          />
          <rect
            x={rightEyeX + 30 - eyeW / 2}
            y={eyeY + 30 - eyeH / 2}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="#ffffff"
          />
          
          {/* Eye highlights */}
          <circle
            cx={leftEyeX + 30 - eyeW * 0.1}
            cy={eyeY + 30 - eyeH * 0.15}
            r={eyeW * 0.15}
            fill="rgba(255,255,255,0.95)"
            opacity={eyeOpen}
          />
          <circle
            cx={rightEyeX + 30 - eyeW * 0.1}
            cy={eyeY + 30 - eyeH * 0.15}
            r={eyeW * 0.15}
            fill="rgba(255,255,255,0.95)"
            opacity={eyeOpen}
          />
        </g>
      </svg>

      {/* Status indicator (small dot) */}
      <div 
        className="blob-status-indicator"
        style={{
          position: 'absolute',
          bottom: 8,
          right: 8,
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: rgb(displayColors.primary),
          boxShadow: `0 0 6px ${rgba(displayColors.primary, 0.6)}`,
        }}
      />
    </div>
  );
}
