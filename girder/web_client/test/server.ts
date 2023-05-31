import { spawn } from 'child_process';
import { afterAll, beforeAll, beforeEach } from 'vitest';
import { preview, PreviewServer } from 'vite';
import { Browser, chromium, expect, Page } from '@playwright/test';
import { outputCoverageReport, startCoverage } from './coverage';
import { ChildProcessWithoutNullStreams } from 'child_process';

declare module 'vitest' {
  export interface TestContext {
    page: Page,
  }
};

const startServer = async (port: number) => {
  const database = `mongodb://localhost:27017/girder-${port}`;
  const serverProcess = spawn('girder', ['serve', '--database', database, '--port', `${port}`], {
    env: { ...process.env, GIRDER_CORS_ALLOW_ORIGIN: '*' },
  });
  await new Promise<void>((resolve, reject) => {
    serverProcess?.stdout.on('data', (data: string) => {
      console.log(`stdout: ${data}`);
    });
    serverProcess?.stderr.on('data', (data: string) => {
      if (data.includes('ENGINE Bus STARTED')) {
        resolve();
      }
      console.error(`stderr: ${data}`);
    });
    serverProcess?.on('close', (code) => {
      console.log(`child process exited with code ${code}`);
    });
  });
  return serverProcess;
};

export const setupServer = () => {
  let server: PreviewServer;
  let browser: Browser;
  let page: Page;
  let serverProcess: ChildProcessWithoutNullStreams;
  const port = Math.floor(Math.random() * 10000 + 40000);

  beforeAll(async () => {
    server = await preview({ preview: { port: 3000 } });
    browser = await chromium.launch({ headless: true });
    page = await browser.newPage();
    await startCoverage(page);
    serverProcess = await startServer(port);
  })

  afterAll(async () => {
    await outputCoverageReport(page);
    await browser.close();
    await new Promise<void>((resolve, reject) => {
      server.httpServer.close(error => error ? reject(error) : resolve())
    });
    serverProcess?.kill();
  })

  beforeEach(async (context) => {
    context.page = page;
    await page.goto(`http://localhost:3000/?apiRoot=${encodeURIComponent(`http://localhost:${port}/api/v1`)}`);
    await expect(page.getByRole('link', { name: 'About' })).toBeVisible();
  });
};
