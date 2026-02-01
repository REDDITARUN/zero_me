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

const CONNECT_ENDPOINT = import.meta.env.VITE_PIPECAT_CONNECT_ENDPOINT || 'http://localhost:8080/connect';

export function usePipecatAgent(options: UsePipecatAgentOptions = {}): UsePipecatAgentReturn {
  const { onStatusChange, onVolumeChange } = options;

  const [client, setClient] = useState<PipecatClient | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('idle');
  const [userVolume, setUserVolume] = useState(0);

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const volumeIntervalRef = useRef<number | null>(null);
  const clientRef = useRef<PipecatClient | null>(null);

  const updateStatus = useCallback((status: AgentStatus) => {
    setAgentStatus(status);
    onStatusChange?.(status);
  }, [onStatusChange]);

  // Monitor microphone volume for visualization
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
          setUserVolume(normalized);
          onVolumeChange?.(normalized);
        }
      }, 50);
    } catch (error) {
      console.error('Failed to access microphone:', error);
    }
  }, [onVolumeChange]);

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

  const connect = useCallback(async () => {
    updateStatus('connecting');

    try {
      const pcClient = new PipecatClient({
        transport: new DailyTransport(),
        enableMic: true,
        enableCam: false,
        callbacks: {
          onConnected: () => {
            console.log('Connected to Pipecat/Daily');
            setIsConnected(true);
            updateStatus('listening');
            startVolumeMonitoring();
          },
          onDisconnected: () => {
            console.log('Disconnected from Pipecat/Daily');
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
            // Could update to a 'user-speaking' state if needed
          },
          onUserStoppedSpeaking: () => {
            console.log('User stopped speaking');
            updateStatus('thinking');
          },
          onError: (error: Error) => {
            console.error('Pipecat error:', error);
            updateStatus('error');
          },
        },
      });

      // Store ref for mic control
      clientRef.current = pcClient;

      // Connect via the connect endpoint
      await pcClient.startBotAndConnect({
        endpoint: CONNECT_ENDPOINT,
      });

      setClient(pcClient);
    } catch (error) {
      console.error('Failed to connect:', error);
      updateStatus('error');
      throw error;
    }
  }, [updateStatus, startVolumeMonitoring, stopVolumeMonitoring]);

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
