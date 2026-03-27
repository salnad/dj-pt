import { evaluate, initStrudel, renderPatternAudio } from "@strudel/web";
import { registerSynthSounds } from "@strudel/webaudio";

export type RenderBrowserRequest = {
  code: string;
  outputPath: string;
  cycles: number;
  cps: number;
  sampleRate: number;
  maxPolyphony: number;
  multiChannelOrbits: boolean;
  format: "wav" | "mp3";
};

export type RenderBrowserResult = {
  success: boolean;
  outputPath: string;
  format: "wav" | "mp3";
  sampleRate: number;
  durationSeconds: number;
  code: string;
  error?: string;
  metadata?: Record<string, unknown>;
};

let initialized = false;

async function ensureInitialized(): Promise<void> {
  if (initialized) {
    return;
  }

  initStrudel();
  await registerSynthSounds();
  initialized = true;
}

async function render(request: RenderBrowserRequest): Promise<RenderBrowserResult> {
  try {
    await ensureInitialized();
    const pattern = await evaluate(request.code, false);
    await renderPatternAudio(
      pattern,
      request.cps,
      0,
      request.cycles,
      request.sampleRate,
      request.maxPolyphony,
      request.multiChannelOrbits,
      request.outputPath,
    );

    return {
      success: true,
      outputPath: request.outputPath,
      format: request.format,
      sampleRate: request.sampleRate,
      durationSeconds: request.cycles / request.cps,
      code: request.code,
      metadata: {
        cycles: request.cycles,
        cps: request.cps,
      },
    };
  } catch (error) {
    return {
      success: false,
      outputPath: request.outputPath,
      format: request.format,
      sampleRate: request.sampleRate,
      durationSeconds: 0,
      code: request.code,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

declare global {
  interface Window {
    __DJPT_RENDER__?: (request: RenderBrowserRequest) => Promise<RenderBrowserResult>;
    __DJPT_RENDERER__?: {
      readonly initialized: boolean;
      readonly render: (request: RenderBrowserRequest) => Promise<RenderBrowserResult>;
    };
  }
}

window.__DJPT_RENDERER__ = {
  get initialized() {
    return initialized;
  },
  render,
};
window.__DJPT_RENDER__ = render;
