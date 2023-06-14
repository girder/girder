import { spawn } from 'child_process';
import { expect } from '@playwright/test';
import { outputCoverageReport, startCoverage } from './coverage';
import { ChildProcessWithoutNullStreams } from 'child_process';
import { test } from '@playwright/test';

const startServer = async (port: number) => {
  const mongoUri = process.env['GIRDER_CLIENT_TESTING_MONGO_URI'] ?? 'mongodb://localhost:27017';
  const girderExecutable = process.env['GIRDER_CLIENT_TESTING_GIRDER_EXECUTABLE'] ?? 'girder';

  const database = `${mongoUri}/girder-${port}`;
  const serverProcess = spawn(girderExecutable, ['serve', '--database', database, '--port', `${port}`], {
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
  let serverProcess: ChildProcessWithoutNullStreams;
  const port = Math.floor(Math.random() * 10000 + 40000);

  test.beforeAll(async ({ browser }) => {
    serverProcess = await startServer(port);
  });

  test.afterAll(async () => {
    serverProcess?.kill();
  });

  test.beforeEach(async ({ page }) => {
    await startCoverage(page);
    await page.goto(`/?apiRoot=${encodeURIComponent(`http://localhost:${port}/api/v1`)}`);
    await expect(page.getByRole('link', { name: 'About' })).toBeVisible();
  });

  test.afterEach(async ({ page }) => {
    await outputCoverageReport(page);
  });
};
