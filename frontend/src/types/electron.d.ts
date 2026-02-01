// Electron API type declarations
import { AgentStatus } from '../context/AgentContext';

export interface ElectronAPI {
  showBlob: () => void;
  hideBlob: () => void;
  minimizeDashboard: () => void;
  showDashboard: () => void;
  sendAgentState: (state: { status: AgentStatus; volume: number }) => void;
  onAgentControl: (callback: (command: string) => void) => void;
  onAgentState: (callback: (state: { status: AgentStatus; volume: number }) => void) => void;
  removeAllListeners: () => void;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}
