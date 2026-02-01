import { useEffect, useRef, useState, useMemo } from 'react';
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
  z: number; // For 3D effect
  vx: number;
  vy: number;
  vz: number;
  size: number;
  opacity: number;
  color: { r: number; g: number; b: number };
  life: number;
  sparkle: number; // Glitter effect
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

// Simplified color scheme
const COLOR_PRESETS: Record<string, ColorSet> = {
  // Coral - idle, connecting, listening
  coral: {
    primary: { r: 245, g: 168, b: 154 },
    secondary: { r: 252, g: 213, b: 207 },
    gradient: ['#fcd5cf', '#f5a89a', '#e8826f'],
  },
  // Blue - agent speaking
  blue: {
    primary: { r: 130, g: 180, b: 245 },
    secondary: { r: 170, g: 210, b: 255 },
    gradient: ['#aad2ff', '#82b4f5', '#5a96e8'],
  },
  // Gray - paused
  gray: {
    primary: { r: 180, g: 180, b: 185 },
    secondary: { r: 210, g: 210, b: 215 },
    gradient: ['#d6d6db', '#b4b4b9', '#9a9a9f'],
  },
};

// Get color preset based on status
function getColorPreset(status: AgentStatus): ColorSet {
  switch (status) {
    case 'speaking':
    case 'thinking':
      return COLOR_PRESETS.blue;
    case 'paused':
      return COLOR_PRESETS.gray;
    default: // idle, connecting, listening, error
      return COLOR_PRESETS.coral;
  }
}

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
  const [currentColors, setCurrentColors] = useState<ColorSet>(COLOR_PRESETS.coral);
  const [targetColors, setTargetColors] = useState<ColorSet>(COLOR_PRESETS.coral);
  const [colorTransition, setColorTransition] = useState(1);
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  // Animation state
  const [pulse, setPulse] = useState(0);
  const [gradPhase, setGradPhase] = useState(0);
  const [eyeLook, setEyeLook] = useState({ x: 0, y: 0 });
  const [eyeOpen, setEyeOpen] = useState(1);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const [glitterParticles, setGlitterParticles] = useState<Particle[]>([]);
  
  const requestRef = useRef<number>();
  const blinkTimeout = useRef<NodeJS.Timeout | null>(null);
  const lookTimeout = useRef<NodeJS.Timeout | null>(null);
  const particleIdRef = useRef(0);
  const rippleIdRef = useRef(0);
  const prevStatusRef = useRef(status);

  // Trigger immersive glitter transition when status changes
  useEffect(() => {
    const newPreset = getColorPreset(status);
    const oldPreset = getColorPreset(prevStatusRef.current);
    
    if (status !== prevStatusRef.current && newPreset !== oldPreset) {
      setTargetColors(newPreset);
      setColorTransition(0);
      setIsTransitioning(true);
      prevStatusRef.current = status;
      
      // Create immersive 3D glitter burst
      const glitterBurst: Particle[] = [];
      const numParticles = 60; // Lots of glitter
      
      for (let i = 0; i < numParticles; i++) {
        // Spherical distribution for 3D effect
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const speed = 1.5 + Math.random() * 3;
        
        // Mix of old and new colors for the transition effect
        const useNewColor = Math.random() > 0.3;
        const color = useNewColor ? newPreset.primary : oldPreset.primary;
        
        glitterBurst.push({
          id: particleIdRef.current++,
          x: size / 2,
          y: size / 2,
          z: 0,
          vx: Math.sin(phi) * Math.cos(theta) * speed,
          vy: Math.sin(phi) * Math.sin(theta) * speed,
          vz: Math.cos(phi) * speed * 0.5,
          size: 1.5 + Math.random() * 4,
          opacity: 0.8 + Math.random() * 0.2,
          color,
          life: 1,
          sparkle: Math.random(), // Random sparkle phase
        });
      }
      
      setGlitterParticles(prev => [...prev, ...glitterBurst]);
      
      // Create swirling ring effect
      const ringParticles: Particle[] = [];
      for (let i = 0; i < 24; i++) {
        const angle = (i / 24) * Math.PI * 2;
        ringParticles.push({
          id: particleIdRef.current++,
          x: size / 2 + Math.cos(angle) * size * 0.4,
          y: size / 2 + Math.sin(angle) * size * 0.4,
          z: 0,
          vx: Math.cos(angle + Math.PI / 2) * 2, // Swirl
          vy: Math.sin(angle + Math.PI / 2) * 2,
          vz: (Math.random() - 0.5) * 2,
          size: 2 + Math.random() * 3,
          opacity: 0.9,
          color: newPreset.primary,
          life: 1.2,
          sparkle: i / 24,
        });
      }
      setGlitterParticles(prev => [...prev, ...ringParticles]);
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
  const isSpeaking = status === 'speaking' || status === 'thinking';

  // Continuous ambient particles
  useEffect(() => {
    if (isActive && volume > 0.02) {
      const count = Math.floor(volume * 3) + 1;
      const newParticles: Particle[] = [];
      
      for (let i = 0; i < count; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = 0.3 + Math.random() * 1 + volume * 1.5;
        newParticles.push({
          id: particleIdRef.current++,
          x: size / 2,
          y: size / 2,
          z: 0,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          vz: (Math.random() - 0.5) * speed,
          size: 1.5 + Math.random() * 3 + volume * 2,
          opacity: 0.5 + Math.random() * 0.4,
          color: displayColors.primary,
          life: 1,
          sparkle: Math.random(),
        });
      }
      
      setParticles(prev => [...prev.slice(-35), ...newParticles]);
    }
  }, [volume, isActive, size, displayColors.primary]);

  // Spawn ripples for audio feedback
  useEffect(() => {
    if (isActive && volume > 0.03) {
      const intensity = Math.min(volume * 2.5, 1);
      setRipples(prev => [...prev.slice(-4), {
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

      // Color transition (smooth over ~500ms)
      setColorTransition(prev => {
        if (prev < 1) {
          const newVal = prev + dt * 2; // ~500ms transition
          if (newVal >= 1) {
            setCurrentColors(targetColors);
            setIsTransitioning(false);
            return 1;
          }
          return newVal;
        }
        return 1;
      });

      // Pulse speed
      const pulseSpeed = isSpeaking ? 2.5 + volume * 3 : isActive ? 1.8 : 1.2;
      setPulse(prev => prev + dt * pulseSpeed);
      setGradPhase(prev => prev + dt * (0.2 + (isActive ? 0.12 : 0) + volume * 0.2));
      
      // Update regular particles
      setParticles(prev => prev
        .map(p => ({
          ...p,
          x: p.x + p.vx,
          y: p.y + p.vy,
          z: p.z + p.vz,
          vx: p.vx * 0.97,
          vy: p.vy * 0.97,
          vz: p.vz * 0.95,
          life: p.life - dt * 0.8,
          opacity: p.opacity * (0.96 - dt * 0.2),
          sparkle: (p.sparkle + dt * 3) % 1,
        }))
        .filter(p => p.life > 0 && p.opacity > 0.02)
      );
      
      // Update glitter particles with 3D sparkle effect
      setGlitterParticles(prev => prev
        .map(p => ({
          ...p,
          x: p.x + p.vx,
          y: p.y + p.vy,
          z: p.z + p.vz,
          vx: p.vx * 0.94,
          vy: p.vy * 0.94,
          vz: p.vz * 0.92,
          life: p.life - dt * 0.6,
          opacity: p.opacity * (0.95 - dt * 0.15),
          sparkle: (p.sparkle + dt * 5) % 1, // Fast sparkle
        }))
        .filter(p => p.life > 0 && p.opacity > 0.02)
      );
      
      // Update ripples
      setRipples(prev => prev
        .map(r => ({ ...r, progress: r.progress + dt * 1.5 }))
        .filter(r => r.progress < 1)
      );

      requestRef.current = requestAnimationFrame(animate);
    };
    
    requestRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(requestRef.current!);
  }, [isSpeaking, volume, isActive, targetColors]);

  // Eye blinking
  useEffect(() => {
    const blink = () => {
      setEyeOpen(0);
      setTimeout(() => setEyeOpen(1), 100 + Math.random() * 60);
      blinkTimeout.current = setTimeout(blink, 2500 + Math.random() * 2500);
    };
    blinkTimeout.current = setTimeout(blink, 2000 + Math.random() * 2000);
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
      lookTimeout.current = setTimeout(look, 1800 + Math.random() * 2200);
    };
    lookTimeout.current = setTimeout(look, 1200);
    return () => { if (lookTimeout.current) clearTimeout(lookTimeout.current); };
  }, []);

  // Geometry
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.35;
  
  // Dynamic scaling
  const speakingBoost = isSpeaking ? volume * 0.12 : 0;
  const transitionBoost = isTransitioning ? 0.08 * Math.sin(colorTransition * Math.PI) : 0;
  const pulseStrength = 0.03 + 0.05 * Math.abs(Math.sin(pulse * 0.7)) + volume * 0.08 + speakingBoost + transitionBoost;
  const scale = 1 + pulseStrength;

  // Gradient animation
  const gradCx = 55 + Math.sin(gradPhase) * 15;
  const gradCy = 35 + Math.cos(gradPhase * 1.3) * 12;

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

  // RGB helpers
  const rgba = (c: { r: number; g: number; b: number }, a: number) => `rgba(${c.r}, ${c.g}, ${c.b}, ${a})`;

  // Calculate 3D particle properties
  const getParticle3D = (p: Particle) => {
    const depth = (p.z + 50) / 100; // Normalize z to 0-1
    const scale3d = 0.5 + depth * 0.8;
    const blur = Math.max(0, (1 - depth) * 2);
    // Sparkle effect - opacity varies with sparkle phase
    const sparkleOpacity = p.opacity * (0.4 + 0.6 * Math.abs(Math.sin(p.sparkle * Math.PI * 2)));
    return { scale3d, blur, sparkleOpacity };
  };

  return (
    <div className="blob-container" style={{ width: size + 80, height: size + 80 }}>
      {/* Glitter particles (3D effect) */}
      <svg 
        className="blob-glitter"
        viewBox={`0 0 ${size + 80} ${size + 80}`}
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'visible' }}
      >
        {glitterParticles.map(p => {
          const { scale3d, blur, sparkleOpacity } = getParticle3D(p);
          return (
            <circle
              key={p.id}
              cx={p.x + 40}
              cy={p.y + 40 - p.z * 0.3} // Slight Y offset for depth
              r={p.size * scale3d}
              fill={rgba(p.color, sparkleOpacity)}
              style={{ filter: blur > 0.5 ? `blur(${blur}px)` : undefined }}
            />
          );
        })}
      </svg>

      {/* Regular particles */}
      <svg 
        className="blob-particles"
        viewBox={`0 0 ${size + 80} ${size + 80}`}
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      >
        {particles.map(p => {
          const { scale3d, sparkleOpacity } = getParticle3D(p);
          return (
            <circle
              key={p.id}
              cx={p.x + 40}
              cy={p.y + 40}
              r={p.size * scale3d}
              fill={rgba(p.color, sparkleOpacity)}
            />
          );
        })}
      </svg>

      {/* Outer glow and ripples */}
      <svg
        className="blob-glow"
        viewBox={`0 0 ${size + 80} ${size + 80}`}
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      >
        <defs>
          <radialGradient id={glowId}>
            <stop offset="0%" stopColor={rgba(displayColors.primary, 0.5)} />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          <filter id={`${glowId}-blur`}>
            <feGaussianBlur stdDeviation={size * 0.1} />
          </filter>
        </defs>
        
        {/* Ambient glow */}
        <circle
          cx={cx + 40}
          cy={cy + 40}
          r={r * (1.9 + (isSpeaking ? 0.3 + volume * 0.4 : 0) + (isTransitioning ? 0.3 : 0))}
          fill={`url(#${glowId})`}
          opacity={0.6 + volume * 0.3 + (isTransitioning ? 0.2 : 0)}
          style={{ filter: `url(#${glowId}-blur)` }}
        />
        
        {/* Ripples */}
        {ripples.map(ripple => (
          <circle
            key={ripple.id}
            cx={cx + 40}
            cy={cy + 40}
            r={r + size * 0.12 + ripple.progress * size * 0.35}
            fill="none"
            stroke={rgba(displayColors.primary, ripple.intensity * (1 - ripple.progress) * 0.5)}
            strokeWidth={2.5 * ripple.intensity * (1 - ripple.progress)}
          />
        ))}
        
        {/* Breathing ring */}
        {isActive && (
          <circle
            cx={cx + 40}
            cy={cy + 40}
            r={r + size * 0.1 + Math.sin(pulse * 0.5) * size * 0.04}
            fill="none"
            stroke={rgba(displayColors.primary, 0.3)}
            strokeWidth={1.5}
          />
        )}
      </svg>

      {/* Main blob sphere */}
      <svg
        className="blob-main"
        viewBox={`0 0 ${size + 80} ${size + 80}`}
        style={{ position: 'absolute', inset: 0 }}
      >
        <defs>
          {/* Main gradient */}
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
            <feDropShadow dx="0" dy="4" stdDeviation="8" floodColor={displayColors.gradient[2]} floodOpacity="0.3"/>
          </filter>
        </defs>

        {/* Shadow on ground */}
        <ellipse
          cx={cx + 40}
          cy={cy + 40 + r * 1.2}
          rx={r * 0.7 * scale}
          ry={r * 0.15}
          fill="rgba(0,0,0,0.1)"
          style={{ filter: 'blur(8px)' }}
        />

        {/* Main sphere body */}
        <circle
          cx={cx + 40}
          cy={cy + 40}
          r={r * scale}
          fill={`url(#${gradientId})`}
          style={{ filter: `url(#${gradientId}-shadow)` }}
        />
        
        {/* Glass overlay */}
        <circle
          cx={cx + 40}
          cy={cy + 40}
          r={r * scale}
          fill={`url(#${overlayId})`}
        />
        
        {/* Inner highlight */}
        <ellipse
          cx={cx + 40 - size * 0.03}
          cy={cy + 40 - size * 0.04}
          rx={r * scale * 0.4}
          ry={r * scale * 0.25}
          fill="rgba(255,255,255,0.5)"
        />

        {/* Eyes */}
        <g className="blob-eyes">
          {/* Eye shadows */}
          <rect
            x={leftEyeX + 40 - eyeW / 2 + 1}
            y={eyeY + 40 - eyeH / 2 + 1}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="rgba(0,0,0,0.1)"
          />
          <rect
            x={rightEyeX + 40 - eyeW / 2 + 1}
            y={eyeY + 40 - eyeH / 2 + 1}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="rgba(0,0,0,0.1)"
          />
          
          {/* Eyes */}
          <rect
            x={leftEyeX + 40 - eyeW / 2}
            y={eyeY + 40 - eyeH / 2}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="#ffffff"
          />
          <rect
            x={rightEyeX + 40 - eyeW / 2}
            y={eyeY + 40 - eyeH / 2}
            width={eyeW}
            height={eyeH}
            rx={eyeRadius}
            fill="#ffffff"
          />
          
          {/* Eye highlights */}
          <circle
            cx={leftEyeX + 40 - eyeW * 0.1}
            cy={eyeY + 40 - eyeH * 0.15}
            r={eyeW * 0.15}
            fill="rgba(255,255,255,0.95)"
            opacity={eyeOpen}
          />
          <circle
            cx={rightEyeX + 40 - eyeW * 0.1}
            cy={eyeY + 40 - eyeH * 0.15}
            r={eyeW * 0.15}
            fill="rgba(255,255,255,0.95)"
            opacity={eyeOpen}
          />
        </g>
      </svg>
    </div>
  );
}
