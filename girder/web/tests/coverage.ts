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

export const startCoverage = async (page: Page) => {
  try {
    await page.coverage.startJSCoverage({ resetOnNavigation: false });
  } catch(e) {
    // Ok if there's an error thrown when we are not on chromium
  }
};

export const outputCoverageReport = async (page: Page) => {
  try {
    const coverage = await page.coverage.stopJSCoverage();
    for (const entry of coverage) {
      if (/plugin_static/.test(entry.url)) {
        /* TODO handle plugin JS files by mapping them back to the correct local file */
        console.warn('Skipping plugin coverage', entry.url);
        continue;
      }
      const converter = v8toIstanbul(
        'dist/assets/index.js',
        0,
        { source: entry.source ?? '' },
        (path) => path.includes('node_modules')
      );
      await converter.load();
      converter.applyCoverage(entry.functions);

      const id = createId(8);
      await fs.writeFile(`coverage/data/istanbul-${id}.json`, JSON.stringify(converter.toIstanbul()));

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
      })
      const report = reports.create('html', {
        skipEmpty: false,
      });
      report.execute(context);
    }
  } catch (e) {
    // Ok if there's an error thrown when we are not on chromium
    console.error('coverage failed', e);
  }
};
