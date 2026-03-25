import { spawn, ChildProcessWithoutNullStreams } from 'child_process';

import getPort from 'get-port';

import { expect, test } from '@playwright/test';

import { outputCoverageReport, startCoverage } from './coverage';

const mongoUri = process.env.GIRDER_CLIENT_TESTING_MONGO_URI ?? 'mongodb://localhost:27017';
const girderExecutable = process.env.GIRDER_CLIENT_TESTING_GIRDER_EXECUTABLE ?? 'girder';


const startServer = async (port: number) => {
  const serverLogs: string[] = [];
  const database = `${mongoUri}/girder-${port}`;
  const serverProcess = spawn(girderExecutable, [
    'serve',
    '--database', database,
    '--port', `${port}`,
    '--with-temp-assetstore',
  ], {
    env: {
      ...process.env,
      GIRDER_SETTING_CORE_CORS_ALLOW_ORIGIN: '*',
      GIRDER_EMAIL_TO_CONSOLE: 'true',
    },
  });
  await new Promise<void>((resolve) => {
    serverProcess?.stdout.on('data', (data: string) => {
      serverLogs.push(`stdout: ${data}`);
      if (data.includes('Girder server running')) {
        resolve();
      }
    });
    serverProcess?.stderr.on('data', (data: string) => {
      serverLogs.push(`stderr: ${data}`);
    });
    serverProcess?.on('close', (code) => {
      serverLogs.push(`child process exited with code ${code}`);
    });
  });
  serverProcess.serverLogs = serverLogs;
  return serverProcess;
};

export const setupServer = () => {
  let serverProcess: ChildProcessWithoutNullStreams;
  let port: number;

  test.beforeAll(async () => {
    port = await getPort();
    serverProcess = await startServer(port);
  });

  test.afterAll(async () => {
    if (process.env.GIRDER_CLIENT_TESTING_KEEP_SERVER_ALIVE) {
      if (serverProcess) {
        console.log('WARNING: Girder server is being kept alive after test ends. Use the following to kill it:');
        console.log(`kill ${serverProcess?.pid}`);
      }
      return;
    }

    serverProcess?.kill();

    const mongoshProcess = spawn('mongosh', [`${mongoUri}/girder-${port}`, '--eval', 'db.dropDatabase();']);

    await new Promise<void>((resolve) => {
      mongoshProcess?.on('close', (code) => {
        if (code === 0) {
          serverProcess.serverLogs.push('mongo database cleaned up');
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
    await expect(async () => {
      if (port !== null) {
        await page.goto(`http://localhost:${port}/`);
      }
      await expect(page.getByRole('link', { name: 'About' })).toBeVisible();
    }).toPass({ timeout: 30000 });
  });

  test.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status !== testInfo.expectedStatus) {
      if (serverProcess?.serverLogs.length > 0) {
        console.log('Server output for failed test:');
        console.log(serverProcess.serverLogs.join(''));
      }
    }
    if (serverProcess) {
      serverProcess.serverLogs = [];
    }
    await outputCoverageReport(page);
  });
};
