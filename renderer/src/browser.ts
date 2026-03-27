import { evaluate, initStrudel, renderPatternAudio } from "@strudel/web";

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
  audioBase64?: string;
  metadata?: Record<string, unknown>;
};

let initialized = false;
let blobUrlToBlob = new Map<string, Blob>();
let activeBlobCapture:
  | ((payload: { blob: Blob; filename: string }) => void)
  | null = null;
let captureInstalled = false;

async function ensureInitialized(): Promise<void> {
  if (initialized) {
    return;
  }

  initStrudel();
  initialized = true;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  return btoa(binary);
}

function installBlobCapture(): void {
  if (captureInstalled) {
    return;
  }
  captureInstalled = true;

  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  const originalClick = HTMLAnchorElement.prototype.click;

  URL.createObjectURL = ((object: Blob | MediaSource) => {
    const url = originalCreateObjectURL.call(URL, object);
    if (object instanceof Blob) {
      console.debug("[djpt-render] captured blob url", url, object.size);
      blobUrlToBlob.set(url, object);
    }
    return url;
  }) as typeof URL.createObjectURL;

  URL.revokeObjectURL = ((url: string) => {
    blobUrlToBlob.delete(url);
    originalRevokeObjectURL.call(URL, url);
  }) as typeof URL.revokeObjectURL;

  HTMLAnchorElement.prototype.click = function click(this: HTMLAnchorElement): void {
    const blob = blobUrlToBlob.get(this.href);
    console.debug("[djpt-render] anchor click", this.href, this.download, Boolean(blob), Boolean(activeBlobCapture));
    if (blob && activeBlobCapture) {
      const capture = activeBlobCapture;
      activeBlobCapture = null;
      capture({
        blob,
        filename: this.download,
      });
      return;
    }
    return originalClick.call(this);
  };

  const originalBodyAppendChild = HTMLBodyElement.prototype.appendChild;
  HTMLBodyElement.prototype.appendChild = function appendChild<T extends Node>(this: HTMLBodyElement, node: T): T {
    if (node instanceof HTMLAnchorElement) {
      const blob = blobUrlToBlob.get(node.href);
      console.debug("[djpt-render] append anchor", node.href, node.download, Boolean(blob));
    }
    return originalBodyAppendChild.call(this, node);
  };
}

function beginBlobCapture(): Promise<{ filename: string; base64: string }> {
  installBlobCapture();
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      activeBlobCapture = null;
      reject(new Error("Rendered audio blob was not captured."));
    }, 5000);

    activeBlobCapture = ({ blob, filename }) => {
      window.clearTimeout(timeout);
      void blob
        .arrayBuffer()
        .then((buffer) =>
          resolve({
            filename,
            base64: arrayBufferToBase64(buffer),
          }),
        )
        .catch(reject);
    };
  });
}

async function render(request: RenderBrowserRequest): Promise<RenderBrowserResult> {
  try {
    await ensureInitialized();
    const pattern = await evaluate(request.code, false);
    const blobCapture = beginBlobCapture();
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
    const captured = await blobCapture;

    return {
      success: true,
      outputPath: request.outputPath,
      format: request.format,
      sampleRate: request.sampleRate,
      durationSeconds: request.cycles / request.cps,
      code: request.code,
      audioBase64: captured.base64,
      metadata: {
        cycles: request.cycles,
        cps: request.cps,
        capturedFileName: captured.filename,
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
