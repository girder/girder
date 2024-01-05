import { spawn, ChildProcessWithoutNullStreams } from 'child_process';

import { expect, test } from '@playwright/test';

import { outputCoverageReport, startCoverage } from './coverage';

const mongoUri = process.env.GIRDER_CLIENT_TESTING_MONGO_URI ?? 'mongodb://localhost:27017';
const girderExecutable = process.env.GIRDER_CLIENT_TESTING_GIRDER_EXECUTABLE ?? 'girder';

const startServer = async (port: number) => {
  const database = `${mongoUri}/girder-${port}`;
  const serverProcess = spawn(girderExecutable, ['serve', '--database', database, '--port', `${port}`], {
    env: { ...process.env, GIRDER_SETTING_CORE_CORS_ALLOW_ORIGIN: '*' },
  });
  await new Promise<void>((resolve) => {
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
  const port = Math.floor(Math.random() * 10000 + 40000); // TODO better port range

  test.beforeAll(async () => {
    serverProcess = await startServer(port);
  });

  test.afterAll(async () => {
    serverProcess?.kill();

    const mongoshProcess = spawn('mongosh', [`${mongoUri}/girder-${port}`, '--eval', 'db.dropDatabase();']);

    await new Promise<void>((resolve) => {
      mongoshProcess?.on('close', (code) => {
        if (code === 0) {
          console.log('mongo database cleaned up');
        } else {
          console.error('mongo database cleanup failed with code', code);
        }

        resolve();
      });

      mongoshProcess?.on('error', (err) => {
        console.error('mongosh process error -- database not cleaned up', err);
        resolve();
      });
    });
  });

  test.beforeEach(async ({ page }) => {
    await startCoverage(page);
    await page.goto(`http://localhost:${port}/`);
    await expect(page.getByRole('link', { name: 'About' })).toBeVisible();
  });

  test.afterEach(async ({ page }) => {
    await outputCoverageReport(page);
  });
};
