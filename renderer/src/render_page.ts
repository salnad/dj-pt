export type BrowserRenderRequest = {
  code: string;
  outputPath?: string;
  cycles?: number;
  cps?: number;
  sampleRate?: number;
  maxPolyphony?: number;
  multiChannelOrbits?: boolean;
};

export type BrowserRenderResult = {
  success: boolean;
  outputPath?: string | null;
  format: string;
  sampleRate?: number | null;
  durationSeconds?: number | null;
  code: string;
  error?: string | null;
  logs: string[];
  metadata?: Record<string, unknown>;
};
