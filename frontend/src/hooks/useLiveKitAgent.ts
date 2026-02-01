import { useState, useCallback, useEffect, useRef } from 'react';
import { Room, RoomEvent, Track, RemoteParticipant, ConnectionState } from 'livekit-client';
import { AgentStatus } from '../context/AgentContext';

interface UseLiveKitAgentOptions {
  onStatusChange?: (status: AgentStatus) => void;
  onVolumeChange?: (volume: number) => void;
}

interface UseLiveKitAgentReturn {
  connect: (url: string, token: string) => Promise<void>;
  disconnect: () => void;
  room: Room | null;
  isConnected: boolean;
  agentStatus: AgentStatus;
  userVolume: number;
  agentVolume: number;
}

export function useLiveKitAgent(options: UseLiveKitAgentOptions = {}): UseLiveKitAgentReturn {
  const { onStatusChange, onVolumeChange } = options;
  
  const [room, setRoom] = useState<Room | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('idle');
  const [userVolume, setUserVolume] = useState(0);
  const [agentVolume, setAgentVolume] = useState(0);
  
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const volumeIntervalRef = useRef<number | null>(null);

  // Update status and notify
  const updateStatus = useCallback((status: AgentStatus) => {
    setAgentStatus(status);
    onStatusChange?.(status);
  }, [onStatusChange]);

  // Monitor microphone volume
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

  // Connect to LiveKit room
  const connect = useCallback(async (url: string, token: string) => {
    updateStatus('connecting');
    
    try {
      const newRoom = new Room({
        adaptiveStream: true,
        dynacast: true,
      });

      // Room event handlers
      newRoom.on(RoomEvent.Connected, () => {
        console.log('Connected to room');
        setIsConnected(true);
        updateStatus('listening');
        startVolumeMonitoring();
      });

      newRoom.on(RoomEvent.Disconnected, () => {
        console.log('Disconnected from room');
        setIsConnected(false);
        updateStatus('idle');
        stopVolumeMonitoring();
      });

      newRoom.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        console.log('Participant connected:', participant.identity);
        
        // Check for agent participant
        if (participant.kind === 'AGENT') {
          // Monitor agent's state attribute
          participant.on('attributesChanged', (attributes) => {
            const agentState = attributes['lk.agent.state'];
            if (agentState) {
              switch (agentState) {
                case 'listening':
                  updateStatus('listening');
                  break;
                case 'thinking':
                  updateStatus('thinking');
                  break;
                case 'speaking':
                  updateStatus('speaking');
                  break;
                default:
                  updateStatus('listening');
              }
            }
          });
        }
      });

      newRoom.on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
        if (track.kind === Track.Kind.Audio && participant.kind === 'AGENT') {
          // Attach agent audio to speakers
          const element = track.attach();
          element.id = 'agent-audio';
          document.body.appendChild(element);
          
          // Monitor agent audio volume
          // (In production, use track.audioLevel or similar)
        }
      });

      newRoom.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach(el => el.remove());
      });

      // Connect and publish local audio
      await newRoom.connect(url, token);
      await newRoom.localParticipant.setMicrophoneEnabled(true);
      
      setRoom(newRoom);
    } catch (error) {
      console.error('Failed to connect:', error);
      updateStatus('error');
    }
  }, [updateStatus, startVolumeMonitoring, stopVolumeMonitoring]);

  // Disconnect from room
  const disconnect = useCallback(() => {
    if (room) {
      room.disconnect();
      setRoom(null);
    }
    stopVolumeMonitoring();
    updateStatus('idle');
    setIsConnected(false);
  }, [room, updateStatus, stopVolumeMonitoring]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connect,
    disconnect,
    room,
    isConnected,
    agentStatus,
    userVolume,
    agentVolume,
  };
}
