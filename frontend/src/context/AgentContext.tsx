import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { PipecatClient } from '@pipecat-ai/client-js';
import { DailyTransport } from '@pipecat-ai/daily-transport';
import { PipecatClientProvider, PipecatClientAudio } from '@pipecat-ai/client-react';

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

// Pipecat connect endpoint
const PIPECAT_CONNECT_ENDPOINT = import.meta.env.VITE_PIPECAT_CONNECT_ENDPOINT || 'http://localhost:8080/connect';

export function AgentProvider({ children }: { children: ReactNode }) {
  const [status, setStatusInternal] = useState<AgentStatus>('idle');
  const [volume, setVolumeInternal] = useState(0);
  const [client, setClient] = useState<PipecatClient | null>(null);
  const clientRef = useRef<PipecatClient | null>(null);
  const volumeIntervalRef = useRef<number | null>(null);
  const micEnabledRef = useRef<boolean>(true);

  const setStatus = useCallback((newStatus: AgentStatus) => {
    setStatusInternal(newStatus);
    window.electronAPI?.sendAgentState({ status: newStatus, volume });
  }, [volume]);

  const setVolume = useCallback((newVolume: number) => {
    setVolumeInternal(newVolume);
  }, []);

  // Monitor local audio for visualization
  // Note: AudioContext is disabled to avoid conflicts with Daily's WebRTC audio
  const startVolumeMonitoring = useCallback(async () => {
    console.log('Volume monitoring started (simulated to avoid AudioContext conflicts)');
    // Simple fallback: simulate volume activity when connected
    volumeIntervalRef.current = window.setInterval(() => {
      const simulatedVolume = 0.3 + Math.random() * 0.2;
      setVolume(simulatedVolume);
    }, 100);
  }, [setVolume]);

  const stopVolumeMonitoring = useCallback(() => {
    if (volumeIntervalRef.current) {
      clearInterval(volumeIntervalRef.current);
      volumeIntervalRef.current = null;
    }
    setVolume(0);
  }, [setVolume]);

  const start = useCallback(async () => {
    setStatus('connecting');
    window.electronAPI?.showBlob();
    window.electronAPI?.minimizeDashboard();

    try {
      const pcClient = new PipecatClient({
        transport: new DailyTransport(),
        enableMic: true,
        enableCam: false,
        callbacks: {
          onConnected: () => {
            console.log('✅ Connected to Pipecat/Daily');
            setStatus('listening');
            startVolumeMonitoring();
          },
          onDisconnected: () => {
            console.log('❌ Disconnected from Pipecat/Daily');
            setStatus('idle');
            stopVolumeMonitoring();
          },
          onBotConnected: () => {
            console.log('🤖 Bot connected to session');
          },
          onBotDisconnected: () => {
            console.log('🤖 Bot disconnected from session');
          },
          onBotReady: () => {
            console.log('🤖 Bot is ready');
            setStatus('listening');
          },
          onBotStartedSpeaking: () => {
            console.log('🔊 Bot started speaking');
            setStatus('speaking');
          },
          onBotStoppedSpeaking: () => {
            console.log('🔇 Bot stopped speaking');
            setStatus('listening');
          },
          onUserStartedSpeaking: () => {
            console.log('🎤 User started speaking');
          },
          onUserStoppedSpeaking: () => {
            console.log('🎤 User stopped speaking');
            setStatus('thinking');
          },
          onError: (error: Error) => {
            console.error('❌ Pipecat error:', error);
            setStatus('error');
          },
        },
      });

      // Connect to the bot via the connect endpoint
      await pcClient.startBotAndConnect({
        endpoint: PIPECAT_CONNECT_ENDPOINT,
      });

      clientRef.current = pcClient;
      setClient(pcClient);  // Trigger re-render for PipecatClientProvider
      micEnabledRef.current = true;

    } catch (error) {
      console.error('Failed to connect:', error);
      setStatus('error');
      window.electronAPI?.showDashboard();
      
      // Show helpful error
      alert(`Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}\n\nMake sure the backend server is running at ${PIPECAT_CONNECT_ENDPOINT}`);
    }
  }, [setStatus, startVolumeMonitoring, stopVolumeMonitoring]);

  const pause = useCallback(async () => {
    if (clientRef.current) {
      // Toggle mic enabled state
      micEnabledRef.current = !micEnabledRef.current;
      clientRef.current.enableMic(micEnabledRef.current);
      setStatus(micEnabledRef.current ? 'listening' : 'paused');
    }
  }, [setStatus]);

  const stop = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
      clientRef.current = null;
      setClient(null);  // Clear client state
    }
    stopVolumeMonitoring();
    setStatus('idle');
    window.electronAPI?.hideBlob();
    window.electronAPI?.showDashboard();
  }, [setStatus, stopVolumeMonitoring]);

  const isActive = status !== 'idle' && status !== 'error';

  // Listen for global shortcut commands from Electron
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
      if (clientRef.current) {
        clientRef.current.disconnect();
      }
      stopVolumeMonitoring();
    };
  }, [stopVolumeMonitoring]);

  return (
    <AgentContext.Provider value={{ status, setStatus, volume, setVolume, start, pause, stop, isActive }}>
      {client ? (
        <PipecatClientProvider client={client}>
          {/* PipecatClientAudio handles bot audio playback automatically */}
          <PipecatClientAudio />
          {children}
        </PipecatClientProvider>
      ) : (
        children
      )}
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
