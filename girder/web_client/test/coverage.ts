import { createCoverageMap } from 'istanbul-lib-coverage';
import v8toIstanbul from 'v8-to-istanbul';
import libReport from 'istanbul-lib-report';
import reports from 'istanbul-reports';
import { Page } from '@playwright/test';

export const startCoverage = async (page: Page) => {
  await page.coverage.startJSCoverage({ resetOnNavigation: false });
};

export const outputCoverageReport = async (page: Page) => {
  const coverage = await page.coverage.stopJSCoverage();
  for (const entry of coverage) {
    const converter = v8toIstanbul('dist/assets/index.js', 0, { source: entry.source ?? '' }, (path) => path.includes('node_modules'));
    await converter.load();
    converter.applyCoverage(entry.functions);
    const coverageMap = createCoverageMap(converter.toIstanbul());

    const context = libReport.createContext({
      dir: 'coverage',
      defaultSummarizer: 'nested',
      watermarks: {
        statements: [50, 80] as [number, number],
        functions: [50, 80] as [number, number],
        branches: [50, 80] as [number, number],
        lines: [50, 80] as [number, number],
      },
      coverageMap,
    })

    const report = reports.create('html', {
      skipEmpty: false,
    });

    report.execute(context);
  }
};
