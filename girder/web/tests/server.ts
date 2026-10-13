import { spawn, ChildProcessWithoutNullStreams } from 'child_process';
import { randomBytes } from 'crypto';

import getPort from 'get-port';

import { expect, test } from '@playwright/test';

import { outputCoverageReport, startCoverage } from './coverage';

const mongoUri = process.env.GIRDER_CLIENT_TESTING_MONGO_URI ?? 'mongodb://localhost:27017';
const girderExecutable = process.env.GIRDER_CLIENT_TESTING_GIRDER_EXECUTABLE ?? 'girder';

/**
 * Build a database name that is unique to this test server instance.
 *
 * This deliberately does not derive the database name from the port alone.
 * Ports are recycled by the OS, so an interrupted prior run could leave a
 * database behind that a later run would then reuse, leaking state (for
 * example, a user registered by a previous run would cause "login already
 * exists" failures). Combining the pid, a timestamp, and random bytes makes
 * collisions effectively impossible.
 */
const createDatabaseName = () =>
  `girder-${process.pid}-${Date.now()}-${randomBytes(4).toString('hex')}`;

/**
 * The mongo shell command used for database cleanup, probed once and memoized
 * for the lifetime of this worker process. `null` means no shell was found, in
 * which case cleanup is skipped: some environments (for example CI images with
 * a MongoDB service but no shell client on the PATH) cannot drop databases
 * this way, and since database names are unique to this process, leftover
 * databases cannot interfere with subsequent runs.
 */
let mongoShell: Promise<string | null> | null = null;

const findMongoShell = (): Promise<string | null> => {
  if (mongoShell === null) {
    mongoShell = new Promise<string | null>((resolve) => {
      const candidates = ['mongosh', 'mongo'];
      let index = 0;
      const probe = () => {
        if (index >= candidates.length) {
          resolve(null);
          return;
        }
        const shellProcess = spawn(candidates[index], ['--version']);
        index += 1;
        shellProcess.on('error', () => probe());
        shellProcess.on('close', (code) => {
          if (code === 0) {
            resolve(candidates[index - 1]);
          } else {
            probe();
          }
        });
      };
      probe();
    });
  }
  return mongoShell;
};

/**
 * Drop a database, waiting for the mongo shell to finish. Failures are
 * reported but never thrown, so that a cleanup problem cannot mask the actual
 * test result. If no mongo shell is available, cleanup is skipped silently.
 */
const dropDatabase = async (database: string) => {
  const shell = await findMongoShell();
  if (shell === null) {
    return;
  }

  const shellProcess = spawn(shell, [`${mongoUri}/${database}`, '--eval', 'db.dropDatabase();']);

  await new Promise<void>((resolve) => {
    shellProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`mongo database ${database} cleanup failed with code`, code);
      }
      resolve();
    });

    shellProcess.on('error', (err) => {
      console.error(`mongo shell process error -- database ${database} not cleaned up`, err);
      resolve();
    });
  });
};

/**
 * Wait for a server process to exit, but do not wait forever if it hangs.
 */
const killServer = async (serverProcess?: ChildProcessWithoutNullStreams) => {
  if (!serverProcess) {
    return;
  }

  await new Promise<void>((resolve) => {
    const timeout = setTimeout(resolve, 5000);
    serverProcess.once('close', () => {
      clearTimeout(timeout);
      resolve();
    });
    serverProcess.kill();
  });
};

/**
 * The captured output of the Girder server started most recently in this
 * worker process. Specs can inspect these logs; for example, emails are
 * written to the server console when GIRDER_EMAIL_TO_CONSOLE is enabled.
 */
const serverLogs: string[] = [];

const startServer = async (port: number, database: string) => {
  serverLogs.length = 0;
  const serverProcess = spawn(girderExecutable, [
    'serve',
    '--database', `${mongoUri}/${database}`,
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
  let database: string;
  let port: number;

  test.beforeAll(async () => {
    port = await getPort();
    database = createDatabaseName();
    serverProcess = await startServer(port, database);
  });

  test.afterAll(async () => {
    if (process.env.GIRDER_CLIENT_TESTING_KEEP_SERVER_ALIVE) {
      if (serverProcess) {
        console.log('WARNING: Girder server is being kept alive after test ends. Use the following to kill it:');
        console.log(`kill ${serverProcess?.pid}`);
        console.log(`Its database is: ${database}`);
      }
      return;
    }

    // Wait for the server to exit before dropping the database, so it cannot
    // recreate collections after the drop.
    await killServer(serverProcess);
    await dropDatabase(database);
  });

  test.beforeEach(async ({ page }) => {
    await startCoverage(page);
    await expect(async () => {
      if (port !== null) {
        await page.goto(`http://localhost:${port}/`);
      }
      await expect(page.getByRole('link', { name: 'About' })).toBeVisible();
    }).toPass({ timeout: 60000 });
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

export { serverLogs };
