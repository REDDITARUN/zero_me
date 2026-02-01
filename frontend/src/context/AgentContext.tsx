import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { Room, RoomEvent, Track, ConnectionState, RemoteParticipant, LocalParticipant } from 'livekit-client';

export type AgentStatus = 'idle' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'paused' | 'error';

interface AgentContextType {
  status: AgentStatus;
  setStatus: (status: AgentStatus) => void;
  volume: number;
  setVolume: (volume: number) => void;
  start: () => void;
  pause: () => void;
  stop: () => void;
  isActive: boolean;
}

const AgentContext = createContext<AgentContextType | null>(null);

// Declare electron API types
declare global {
  interface Window {
    electronAPI?: {
      showBlob: () => void;
      hideBlob: () => void;
      minimizeDashboard: () => void;
      showDashboard: () => void;
      sendAgentState: (state: { status: AgentStatus; volume: number }) => void;
      onAgentControl: (callback: (command: string) => void) => void;
      onAgentState: (callback: (state: { status: AgentStatus; volume: number }) => void) => void;
      removeAllListeners: () => void;
    };
  }
}

// LiveKit connection config - UPDATE THESE or use env vars
const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL || 'wss://demo-jxnrd0np.livekit.cloud';
const LIVEKIT_TOKEN_ENDPOINT = import.meta.env.VITE_TOKEN_ENDPOINT || null;

export function AgentProvider({ children }: { children: ReactNode }) {
  const [status, setStatusInternal] = useState<AgentStatus>('idle');
  const [volume, setVolumeInternal] = useState(0);
  const roomRef = useRef<Room | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const volumeIntervalRef = useRef<number | null>(null);

  const setStatus = useCallback((newStatus: AgentStatus) => {
    setStatusInternal(newStatus);
    window.electronAPI?.sendAgentState({ status: newStatus, volume });
  }, [volume]);

  const setVolume = useCallback((newVolume: number) => {
    setVolumeInternal(newVolume);
  }, []);

  // Fetch token from endpoint or use sandbox
  const getToken = async (): Promise<string> => {
    if (LIVEKIT_TOKEN_ENDPOINT) {
      const response = await fetch(LIVEKIT_TOKEN_ENDPOINT);
      const data = await response.json();
      return data.token;
    }
    
    // Use LiveKit Cloud Sandbox for development
    // Go to: https://cloud.livekit.io/projects/p_/sandbox
    // Create a token server sandbox and get the endpoint
    throw new Error('No token endpoint configured. Set VITE_TOKEN_ENDPOINT in frontend/.env.local or use LiveKit Cloud Sandbox.');
  };

  // Monitor local audio for visualization
  const startVolumeMonitoring = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      analyserRef.current.fftSize = 256;
      
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      
      volumeIntervalRef.current = window.setInterval(() => {
        if (analyserRef.current) {
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
          const normalized = average / 255;
          setVolume(normalized);
        }
      }, 50);
    } catch (error) {
      console.error('Failed to access microphone:', error);
    }
  }, [setVolume]);

  const stopVolumeMonitoring = useCallback(() => {
    if (volumeIntervalRef.current) {
      clearInterval(volumeIntervalRef.current);
      volumeIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
  }, []);

  const start = useCallback(async () => {
    setStatus('connecting');
    window.electronAPI?.showBlob();
    window.electronAPI?.minimizeDashboard();

    try {
      const token = await getToken();
      
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });

      // Connection events
      room.on(RoomEvent.Connected, () => {
        console.log('✅ Connected to LiveKit room');
        setStatus('listening');
        startVolumeMonitoring();
      });

      room.on(RoomEvent.Disconnected, () => {
        console.log('❌ Disconnected from room');
        setStatus('idle');
        stopVolumeMonitoring();
      });

      // Helper to monitor agent state
      const monitorAgentState = (participant: RemoteParticipant) => {
        const checkAgentState = () => {
          const agentState = participant.attributes?.['lk.agent.state'];
          if (agentState) {
            console.log('🤖 Agent state changed:', agentState);
            switch (agentState) {
              case 'initializing':
                setStatus('connecting');
                break;
              case 'listening':
                setStatus('listening');
                break;
              case 'thinking':
                setStatus('thinking');
                break;
              case 'speaking':
                setStatus('speaking');
                break;
            }
          }
        };

        // Check initial state
        checkAgentState();
        
        // Listen for changes
        participant.on('attributesChanged', () => {
          checkAgentState();
        });
      };

      // Agent participant events
      room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        console.log('👤 Participant connected:', participant.identity);
        
        // Check if this is an agent (identity starts with 'agent-')
        if (participant.identity.startsWith('agent-')) {
          console.log('🤖 Agent joined the room');
          monitorAgentState(participant);
        }
      });

      // Also check existing participants when we connect (agent might already be there)
      room.on(RoomEvent.Connected, () => {
        room.remoteParticipants.forEach((participant) => {
          if (participant.identity.startsWith('agent-')) {
            console.log('🤖 Found existing agent in room');
            monitorAgentState(participant);
          }
        });
      });

      // Handle agent audio
      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        console.log('🎵 Track subscribed:', track.kind, 'from', participant.identity);
        
        if (track.kind === Track.Kind.Audio) {
          const element = track.attach();
          element.id = `audio-${participant.identity}`;
          document.body.appendChild(element);
          console.log('🔊 Audio attached');
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach(el => el.remove());
      });

      // Connect
      await room.connect(LIVEKIT_URL, token);
      console.log('🎤 Enabling microphone...');
      await room.localParticipant.setMicrophoneEnabled(true);
      
      roomRef.current = room;

    } catch (error) {
      console.error('Failed to connect:', error);
      setStatus('error');
      window.electronAPI?.showDashboard();
      
      // Show helpful error
      alert(`Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}\n\nMake sure you have VITE_TOKEN_ENDPOINT set in frontend/.env.local`);
    }
  }, [setStatus, startVolumeMonitoring, stopVolumeMonitoring]);

  const pause = useCallback(async () => {
    if (roomRef.current) {
      const isMuted = roomRef.current.localParticipant.isMicrophoneEnabled;
      await roomRef.current.localParticipant.setMicrophoneEnabled(!isMuted);
      setStatus(isMuted ? 'listening' : 'paused');
    }
  }, [setStatus]);

  const stop = useCallback(() => {
    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }
    stopVolumeMonitoring();
    setStatus('idle');
    window.electronAPI?.hideBlob();
    window.electronAPI?.showDashboard();
  }, [setStatus, stopVolumeMonitoring]);

  const isActive = status !== 'idle' && status !== 'error';

  // Listen for global shortcut commands
  useEffect(() => {
    window.electronAPI?.onAgentControl((command) => {
      switch (command) {
        case 'start':
          if (!isActive) start();
          break;
        case 'pause':
          pause();
          break;
        case 'stop':
          if (isActive) stop();
          break;
      }
    });

    // Sync state from other windows
    window.electronAPI?.onAgentState((state) => {
      setStatusInternal(state.status);
      setVolumeInternal(state.volume);
    });

    return () => {
      window.electronAPI?.removeAllListeners();
    };
  }, [isActive, start, pause, stop]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
      }
      stopVolumeMonitoring();
    };
  }, [stopVolumeMonitoring]);

  return (
    <AgentContext.Provider value={{ status, setStatus, volume, setVolume, start, pause, stop, isActive }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgent() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgent must be used within AgentProvider');
  }
  return context;
}
