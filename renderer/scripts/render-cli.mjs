import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";

import puppeteer from "puppeteer-core";

function parseArgs(argv) {
  const args = {};
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--job-json") {
      args.jobJson = argv[index + 1];
      index += 1;
    } else if (token === "--page-url") {
      args.pageUrl = argv[index + 1];
      index += 1;
    } else if (token === "--chrome") {
      args.chrome = argv[index + 1];
      index += 1;
    }
  }
  return args;
}

async function ensureOutputDir(targetPath) {
  const outputDir = path.dirname(targetPath);
  await fs.mkdir(outputDir, { recursive: true });
}

function contentTypeFor(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".js")) return "application/javascript; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".map")) return "application/json; charset=utf-8";
  if (filePath.endsWith(".svg")) return "image/svg+xml";
  return "application/octet-stream";
}

async function startStaticServer(rootDirectory) {
  const server = http.createServer(async (request, response) => {
    try {
      const requestPath = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
      const relativePath = requestPath === "/" ? "index.html" : requestPath.replace(/^\/+/, "");
      const fullPath = path.join(rootDirectory, relativePath);
      if (!fullPath.startsWith(rootDirectory)) {
        response.writeHead(403);
        response.end("Forbidden");
        return;
      }
      const contents = await fs.readFile(fullPath);
      response.writeHead(200, { "content-type": contentTypeFor(fullPath) });
      response.end(contents);
    } catch (error) {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end(`Not found: ${error instanceof Error ? error.message : String(error)}`);
    }
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("Failed to determine static server address.");
  }
  return {
    server,
    url: `http://127.0.0.1:${address.port}/index.html`,
  };
}

async function waitForDownload(downloadPath, timeoutMs = 30000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const entries = await fs.readdir(path.dirname(downloadPath));
      const basename = path.basename(downloadPath);
      const exact = entries.find((entry) => entry === basename);
      const partial = entries.find((entry) => entry.startsWith(basename) && !entry.endsWith(".crdownload"));
      const fileName = exact || partial;
      if (fileName) {
        return path.join(path.dirname(downloadPath), fileName);
      }
    } catch {
      // continue polling
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for download at ${downloadPath}`);
}

async function convertWithFfmpeg(inputPath, outputPath) {
  await new Promise((resolve, reject) => {
    const child = spawn("ffmpeg", ["-y", "-i", inputPath, "-codec:a", "libmp3lame", "-b:a", "192k", outputPath], {
      stdio: ["ignore", "ignore", "pipe"],
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("exit", (code) => {
      if (code === 0) {
        resolve(undefined);
      } else {
        reject(new Error(`ffmpeg conversion failed with code ${code}: ${stderr}`));
      }
    });
    child.on("error", reject);
  });
}

async function writeBase64Audio(base64, outputPath) {
  const buffer = Buffer.from(base64, "base64");
  await fs.writeFile(outputPath, buffer);
}

function normalizeJob(renderJob) {
  const outputPath = renderJob.output_path || renderJob.outputPath;
  if (!outputPath) {
    throw new Error("Render job must include output_path or outputPath.");
  }
  return {
    code: renderJob.code,
    outputPath,
    cycles: Number(renderJob.cycles),
    cps: Number(renderJob.cps),
    sampleRate: Number(renderJob.sample_rate || renderJob.sampleRate),
    maxPolyphony: Number(renderJob.max_polyphony || renderJob.maxPolyphony),
    multiChannelOrbits: Boolean(renderJob.multi_channel_orbits || renderJob.multiChannelOrbits),
    format: renderJob.format || path.extname(outputPath).slice(1) || "wav",
  };
}

async function cleanupDirectory(targetPath) {
  try {
    await fs.rm(targetPath, { recursive: true, force: true });
  } catch {
    // ignore cleanup failures
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.jobJson) {
    throw new Error("Missing --job-json payload.");
  }

  const job = JSON.parse(args.jobJson);
  const rootDir = process.cwd();
  const distDir = path.join(rootDir, "renderer", "dist");

  const executablePath =
    args.chrome ||
    process.env.DJPT_CHROME_PATH ||
    "/usr/local/bin/google-chrome";

  const outputPath = job.output_path || job.outputPath;
  if (!outputPath) {
    throw new Error("Render job must include output_path or outputPath.");
  }
  await ensureOutputDir(outputPath);

  const outputDirectory = path.dirname(outputPath);
  const tempDownloadDir = await fs.mkdtemp(path.join(outputDirectory, ".djpt-download-"));
  const { server, url } = await startStaticServer(distDir);
  const pageUrl = args.pageUrl || url;

  const browser = await puppeteer.launch({
    executablePath,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--autoplay-policy=no-user-gesture-required"],
  });

  try {
    const page = await browser.newPage();
    page.on("console", (message) => {
      process.stderr.write(`[renderer:${message.type()}] ${message.text()}\n`);
    });
    page.on("pageerror", (error) => {
      process.stderr.write(`[renderer:pageerror] ${error.message}\n`);
    });
    await page.goto(pageUrl, { waitUntil: "networkidle0" });
    await page.waitForFunction(() => Boolean(window.__DJPT_RENDERER__?.render));
    const result = await page.evaluate(async (renderJob) => {
      return window.__DJPT_RENDERER__.render(renderJob);
    }, normalizeJob({
      ...job,
      outputPath: path.parse(outputPath).name,
      output_path: path.parse(outputPath).name,
    }));
    if (!result.success) {
      throw new Error(result.error || "Renderer page returned failure.");
    }
    if (!result.audioBase64) {
      throw new Error("Renderer page did not provide audioBase64.");
    }
    const tempWavePath = path.join(tempDownloadDir, `${path.parse(outputPath).name}.wav`);
    await writeBase64Audio(result.audioBase64, tempWavePath);
    if ((job.format || path.extname(outputPath).slice(1)) === "mp3") {
      await convertWithFfmpeg(tempWavePath, outputPath);
    } else {
      await fs.rename(tempWavePath, outputPath);
    }
    await fs.rm(tempDownloadDir, { recursive: true, force: true });
    delete result.audioBase64;
    result.outputPath = outputPath;
    result.output_path = outputPath;
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
    await cleanupDirectory(tempDownloadDir);
  }
}

main().catch((error) => {
  const payload = {
    success: false,
    code: "",
    error: error instanceof Error ? error.message : String(error),
    logs: [],
    metadata: {},
  };
  process.stdout.write(`${JSON.stringify(payload)}\n`);
  process.exitCode = 1;
});
