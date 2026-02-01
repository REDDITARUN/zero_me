/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PIPECAT_MODE: string;
  readonly VITE_PIPECAT_CLOUD_AGENT_NAME: string;
  readonly VITE_PIPECAT_CLOUD_API_KEY: string;
  readonly VITE_PIPECAT_CONNECT_ENDPOINT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
