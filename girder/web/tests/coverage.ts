import fs from 'fs/promises';

import v8toIstanbul from 'v8-to-istanbul';
import libReport from 'istanbul-lib-report';
import reports from 'istanbul-reports';
import { Page } from '@playwright/test';
import libCoverage from 'istanbul-lib-coverage';

const createId = (length: number) => {
  let result = '';
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  const charactersLength = characters.length;
  let counter = 0;
  while (counter < length) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
    counter += 1;
  }
  return result;
};

// The main application can be instrumented with istanbul when
// GIRDER_TEST_COVERAGE is set at build time (see vite.config.ts).  Its
// coverage is then read from window.__coverage__, which reports statements,
// branches, and functions exactly (unlike V8 coverage, which credits lines
// inside functions that were never called whenever an enclosing range
// executed).  Detection is done at runtime so it does not matter whether the
// test process also has the variable set.

/**
 * Persist one istanbul coverage map and emit the per-test HTML report for it.
 */
const writeCoverage = async (data: object) => {
  const id = createId(8);
  await fs.writeFile(`coverage/data/istanbul-${id}.json`, JSON.stringify(data));

  // Output per-test coverage report
  // This is probably not useful long-term but has been helpful for debugging coverage testing.
  const map = libCoverage.createCoverageMap(
    JSON.parse((await fs.readFile(`coverage/data/istanbul-${id}.json`)).toString())
  );
  const context = libReport.createContext({
    dir: `coverage/report-${id}`,
    defaultSummarizer: 'nested',
    watermarks: {
      statements: [50, 80] as [number, number],
      functions: [50, 80] as [number, number],
      branches: [50, 80] as [number, number],
      lines: [50, 80] as [number, number],
    },
    coverageMap: map,
  });
  const report = reports.create('html', {
    skipEmpty: false,
  });
  report.execute(context);
};

export const startCoverage = async (page: Page) => {
  try {
    await page.coverage.startJSCoverage({ resetOnNavigation: false });
  } catch(e) {
    // Ok if there's an error thrown when we are not on chromium
  }
};

export const outputCoverageReport = async (page: Page) => {
  // Collect instrumented (istanbul) coverage for the main application first,
  // if the build was instrumented (see vite.config.ts).  This reports
  // statements, branches, and functions exactly, and it is also available on
  // browsers other than chromium.
  let mainInstrumented = false;
  const instrumentedKeys: string[] = [];
  try {
    const istanbulCoverage = await page.evaluate(() => {
      // @ts-ignore - injected by the istanbul instrumentation
      return window.__coverage__;
    });
    if (istanbulCoverage && Object.keys(istanbulCoverage).length > 0) {
      instrumentedKeys.push(...Object.keys(istanbulCoverage));
      await writeCoverage(istanbulCoverage);
      mainInstrumented = true;
    }
  } catch (e) {
    // The page may have been closed, or the build may not have been
    // instrumented; fall through to any V8 coverage.
  }

  let coverage;
  try {
    coverage = await page.coverage.stopJSCoverage();
  } catch (e) {
    return;
  }
  try {
    for (const entry of coverage) {
      const isPlugin = /plugin_static/.test(entry.url);
      const urlParts = entry.url.split('/');
      const plugin = urlParts[urlParts.length - 2].replace(/-/g, '_');
      if (isPlugin) {
        // Skip V8 coverage for a plugin whose source was instrumented with
        // istanbul; its exact coverage is already in window.__coverage__
        // above (the instrumented UMD bundle writes into the same global).
        if (instrumentedKeys.some((key) => key.includes(`/plugins/${plugin}/`))) {
          continue;
        }
      } else if (mainInstrumented) {
        // The application bundle was instrumented, so skip its V8 coverage
        // here.  Converting it as well would re-introduce the over-reported
        // line coverage that the instrumentation exists to avoid.
        continue;
      }
      let converter;
      if (isPlugin) {
        const [filename] = urlParts[urlParts.length - 1].split('?');
        const pathsToCheck = [
          `../../plugins/${plugin}/girder_${plugin}/web_client/dist/${filename}`,
          `../../plugins/${plugin}/girder_plugin_${plugin}/web_client/dist/${filename}`,
          `../../plugins/${plugin}/${plugin}/web_client/dist/${filename}`
        ];
        let path;
        for (const p of pathsToCheck) {
          try {
            await fs.access(p);
            path = p;
            break;
          } catch (e) {
          }
        }
        if (!path) {
          // Plugin static files not found - this is expected for some plugin combinations
          continue;
        }
        converter = v8toIstanbul(
          path,
          0,
          { source: entry.source ?? '' },
          (path) => path.includes('node_modules')
        );
      } else {
        converter = v8toIstanbul(
          'dist/assets/index.js',
          0,
          { source: entry.source ?? '' },
          (path) => path.includes('node_modules')
        );
      }
      await converter.load();
      converter.applyCoverage(entry.functions);

      await writeCoverage(converter.toIstanbul());
    }
  } catch (e) {
    // Coverage processing failed silently

  }
};
