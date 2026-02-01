import { useEffect, useState } from 'react';
import Blob from './Blob';
import { useAgent } from '../context/AgentContext';
import './BlobWindow.css';

export default function BlobWindow() {
  const { status, volume } = useAgent();
  const [simulatedVolume, setSimulatedVolume] = useState(0);

  // Hide scrollbars and set blob mode on body
  useEffect(() => {
    document.body.classList.add('blob-mode');
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    
    return () => {
      document.body.classList.remove('blob-mode');
      document.body.style.overflow = '';
      document.documentElement.style.overflow = '';
    };
  }, []);

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

  return (
    <div className="blob-window" style={{ overflow: 'hidden' }}>
      <Blob 
        status={status} 
        volume={volume > 0 ? volume : simulatedVolume} 
        size={120} 
      />
    </div>
  );
}
