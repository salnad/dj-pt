import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

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

async function main() {
  const args = parseArgs(process.argv);
  if (!args.jobJson) {
    throw new Error("Missing --job-json payload.");
  }

  const job = JSON.parse(args.jobJson);
  const rootDir = process.cwd();
  const distUrl =
    args.pageUrl ||
    pathToFileURL(path.join(rootDir, "renderer", "dist", "index.html")).href;

  const executablePath =
    args.chrome ||
    process.env.DJPT_CHROME_PATH ||
    "/usr/local/bin/google-chrome";

  const outputPath = job.output_path || job.outputPath;
  if (!outputPath) {
    throw new Error("Render job must include output_path or outputPath.");
  }
  await ensureOutputDir(outputPath);

  const browser = await puppeteer.launch({
    executablePath,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--autoplay-policy=no-user-gesture-required"],
  });

  try {
    const page = await browser.newPage();
    await page.goto(distUrl, { waitUntil: "networkidle0" });
    await page.waitForFunction(() => Boolean(window.__DJPT_RENDERER__?.render));
    const result = await page.evaluate(async (renderJob) => {
      return window.__DJPT_RENDERER__.render(renderJob);
    }, job);
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    await browser.close();
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
