import { useState, useCallback, useEffect, useRef } from 'react';
import { PipecatClient } from '@pipecat-ai/client-js';
import { DailyTransport } from '@pipecat-ai/daily-transport';
import { AgentStatus } from '../context/AgentContext';

interface UsePipecatAgentOptions {
  onStatusChange?: (status: AgentStatus) => void;
  onVolumeChange?: (volume: number) => void;
}

interface UsePipecatAgentReturn {
  connect: () => Promise<void>;
  disconnect: () => void;
  client: PipecatClient | null;
  isConnected: boolean;
  agentStatus: AgentStatus;
  userVolume: number;
  setMicEnabled: (enabled: boolean) => void;
}

// Configuration for Pipecat Cloud vs Local mode
const PIPECAT_MODE = import.meta.env.VITE_PIPECAT_MODE || 'cloud';
const PIPECAT_CLOUD_AGENT_NAME = import.meta.env.VITE_PIPECAT_CLOUD_AGENT_NAME || 'zero-me-assistant';
const PIPECAT_CLOUD_API_KEY = import.meta.env.VITE_PIPECAT_CLOUD_API_KEY || '';
const LOCAL_CONNECT_ENDPOINT = import.meta.env.VITE_PIPECAT_CONNECT_ENDPOINT || 'http://localhost:8080/connect';

// Pipecat Cloud API endpoint
const PIPECAT_CLOUD_API_URL = 'https://api.pipecat.daily.co/v1/public';

export function usePipecatAgent(options: UsePipecatAgentOptions = {}): UsePipecatAgentReturn {
  const { onStatusChange, onVolumeChange } = options;

  const [client, setClient] = useState<PipecatClient | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('idle');
  const [userVolume, setUserVolume] = useState(0);

  const volumeIntervalRef = useRef<number | null>(null);
  const clientRef = useRef<PipecatClient | null>(null);

  const updateStatus = useCallback((status: AgentStatus) => {
    setAgentStatus(status);
    onStatusChange?.(status);
  }, [onStatusChange]);

  // Simple volume simulation for UI visualization
  const startVolumeMonitoring = useCallback(() => {
    volumeIntervalRef.current = window.setInterval(() => {
      const simulatedVolume = 0.3 + Math.random() * 0.2;
      setUserVolume(simulatedVolume);
      onVolumeChange?.(simulatedVolume);
    }, 100);
  }, [onVolumeChange]);

  const stopVolumeMonitoring = useCallback(() => {
    if (volumeIntervalRef.current) {
      clearInterval(volumeIntervalRef.current);
      volumeIntervalRef.current = null;
    }
    setUserVolume(0);
  }, []);

  /**
   * Connect using Pipecat Cloud API
   */
  const connectPipecatCloud = useCallback(async (): Promise<{ room_url: string; token: string }> => {
    console.log(`Connecting to Pipecat Cloud agent: ${PIPECAT_CLOUD_AGENT_NAME}`);
    
    const response = await fetch(`${PIPECAT_CLOUD_API_URL}/${PIPECAT_CLOUD_AGENT_NAME}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(PIPECAT_CLOUD_API_KEY && { 'Authorization': `Bearer ${PIPECAT_CLOUD_API_KEY}` }),
      },
      body: JSON.stringify({
        createDailyRoom: true,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to start Pipecat Cloud session: ${error}`);
    }

    const data = await response.json();
    return {
      room_url: data.dailyRoom,
      token: data.dailyToken,
    };
  }, []);

  /**
   * Connect using local self-hosted server
   */
  const connectLocal = useCallback(async (): Promise<{ room_url: string; token: string }> => {
    console.log(`Connecting to local server: ${LOCAL_CONNECT_ENDPOINT}`);
    
    const response = await fetch(LOCAL_CONNECT_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to connect to local server: ${error}`);
    }

    return await response.json();
  }, []);

  const connect = useCallback(async () => {
    updateStatus('connecting');

    try {
      // Get room URL and token based on mode
      let connectionData: { room_url: string; token: string };
      
      if (PIPECAT_MODE === 'cloud') {
        connectionData = await connectPipecatCloud();
      } else {
        connectionData = await connectLocal();
      }

      console.log('Got connection data, joining Daily room...');

      // Create Pipecat client with Daily transport
      // Audio playback is handled by PipecatClientAudio component from @pipecat-ai/client-react
      const pcClient = new PipecatClient({
        transport: new DailyTransport(),
        enableMic: true,
        enableCam: false,
        callbacks: {
          onConnected: () => {
            console.log('Connected to Daily room');
            setIsConnected(true);
            updateStatus('listening');
            startVolumeMonitoring();
          },
          onDisconnected: () => {
            console.log('Disconnected from Daily room');
            setIsConnected(false);
            updateStatus('idle');
            stopVolumeMonitoring();
          },
          onBotConnected: () => {
            console.log('Bot connected to session');
          },
          onBotDisconnected: () => {
            console.log('Bot disconnected from session');
          },
          onBotReady: () => {
            console.log('Bot is ready');
            updateStatus('listening');
          },
          onBotStartedSpeaking: () => {
            console.log('Bot started speaking');
            updateStatus('speaking');
          },
          onBotStoppedSpeaking: () => {
            console.log('Bot stopped speaking');
            updateStatus('listening');
          },
          onUserStartedSpeaking: () => {
            console.log('User started speaking');
          },
          onUserStoppedSpeaking: () => {
            console.log('User stopped speaking');
            updateStatus('thinking');
          },
          onError: (error: unknown) => {
            console.error('Pipecat error:', error);
            updateStatus('error');
          },
        },
      });

      // Store ref for mic control
      clientRef.current = pcClient;

      // Connect to the Daily room
      await pcClient.connect({
        url: connectionData.room_url,
        token: connectionData.token,
      });

      setClient(pcClient);
    } catch (error) {
      console.error('Failed to connect:', error);
      updateStatus('error');
      throw error;
    }
  }, [updateStatus, startVolumeMonitoring, stopVolumeMonitoring, connectPipecatCloud, connectLocal]);

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
      clientRef.current = null;
    }
    setClient(null);
    stopVolumeMonitoring();
    updateStatus('idle');
    setIsConnected(false);
  }, [updateStatus, stopVolumeMonitoring]);

  const setMicEnabled = useCallback((enabled: boolean) => {
    if (clientRef.current) {
      clientRef.current.enableMic(enabled);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
      }
      stopVolumeMonitoring();
    };
  }, [stopVolumeMonitoring]);

  return {
    connect,
    disconnect,
    client,
    isConnected,
    agentStatus,
    userVolume,
    setMicEnabled,
  };
}
