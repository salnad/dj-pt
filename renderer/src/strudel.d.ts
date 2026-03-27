declare module "@strudel/web" {
  export function initStrudel(options?: unknown): void;
  export function evaluate(code: string, shouldPlay?: boolean): Promise<unknown>;
  export function renderPatternAudio(
    pattern: unknown,
    cps: number,
    fromCycle: number,
    toCycle: number,
    sampleRate: number,
    maxPolyphony: number,
    multiChannelOrbits: boolean,
    fileName?: string,
  ): Promise<void>;
}

declare module "@strudel/webaudio" {
  export function registerSynthSounds(): Promise<void>;
}
