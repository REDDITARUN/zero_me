const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Window controls
  showBlob: () => ipcRenderer.send('show-blob'),
  hideBlob: () => ipcRenderer.send('hide-blob'),
  minimizeDashboard: () => ipcRenderer.send('minimize-dashboard'),
  showDashboard: () => ipcRenderer.send('show-dashboard'),

  // Agent state sync
  sendAgentState: (state) => ipcRenderer.send('agent-state', state),

  // Listen for agent control commands (from global shortcuts)
  onAgentControl: (callback) => {
    ipcRenderer.on('agent-control', (event, command) => callback(command));
  },

  // Listen for agent state updates (from other windows)
  onAgentState: (callback) => {
    ipcRenderer.on('agent-state', (event, state) => callback(state));
  },

  // Cleanup listeners
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('agent-control');
    ipcRenderer.removeAllListeners('agent-state');
  },
});
