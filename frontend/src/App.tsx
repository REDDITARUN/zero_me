import { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import BlobWindow from './components/BlobWindow';
import { AgentProvider } from './context/AgentContext';

// Simple hash-based routing for Electron windows
function App() {
  const [route, setRoute] = useState(window.location.hash || '#/');

  useEffect(() => {
    const handleHashChange = () => setRoute(window.location.hash || '#/');
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  return (
    <AgentProvider>
      {route === '#/blob' ? <BlobWindow /> : <Dashboard />}
    </AgentProvider>
  );
}

export default App;
