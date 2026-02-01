import { useEffect, useState } from 'react';
import Blob from './Blob';
import { useAgent } from '../context/AgentContext';
import './BlobWindow.css';

export default function BlobWindow() {
  const { status, volume } = useAgent();
  const [simulatedVolume, setSimulatedVolume] = useState(0);

  // Simulate volume fluctuations for demo (replace with real audio analysis)
  useEffect(() => {
    if (status === 'listening' || status === 'speaking') {
      const interval = setInterval(() => {
        // Simulate audio volume with some randomness
        const baseVolume = status === 'speaking' ? 0.4 : 0.2;
        const variation = Math.random() * 0.4;
        setSimulatedVolume(baseVolume + variation);
      }, 100);
      
      return () => clearInterval(interval);
    } else {
      setSimulatedVolume(0);
    }
  }, [status]);

  // For demo, cycle through states
  useEffect(() => {
    if (status === 'listening') {
      const timeout = setTimeout(() => {
        // This would be triggered by actual voice detection
        // For demo, we cycle back
      }, 5000);
      return () => clearTimeout(timeout);
    }
  }, [status]);

  return (
    <div className="blob-window">
      <Blob 
        status={status} 
        volume={volume > 0 ? volume : simulatedVolume} 
        size={120} 
      />
    </div>
  );
}
