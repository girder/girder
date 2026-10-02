import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, waitForIdlePage } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function asyncRestRequest(page: Page, opts: any) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            window.girder.rest.restRequest(opts).done((resp: any) => {
                resolve(resp);
            }).fail((resp: any) => {
                reject(resp);
            });
        });
    }, opts);
}

async function createCliItem(page: Page, { specFile = 'slicer_cli_web_test.xml', name = 'Slicer CLI Web Test' } = {}) {
    const resp = await asyncRestRequest(page, {
        url: '/folder',
        data: { text: 'Public', limit: 1 },
    }) as any[];
    const folderId = resp[0]._id;
    const data = fs.readFileSync(path.join(__dirname, 'data', specFile));
    const base64data = Buffer.from(data).toString('base64');

    await asyncRestRequest(page, {
        url: '/slicer_cli_web/cli',
        method: 'POST',
        data: {
            folder: folderId,
            image: 'girder/slicer_cli_web_test:latest',
            name,
            desc_type: 'xml',
            spec: base64data,
            replace: false,
        },
    });
}

/**
 * The legacy dockerTaskSpec.js covered importing a docker image and running a
 * task, both of which need a worker and a docker daemon. The docker ingestion
 * behavior lives in test/slicer_cli_web_tests/test_docker.py; here we only keep
 * the UI rendering checks that do not require a worker.
 */
test.describe('Slicer CLI web task rendering', () => {
    setupServer();

    test('render a task and toggle its panel', async ({ page }) => {
        await createUser(page, 'admin');
        await createCliItem(page);
        await waitForIdlePage(page);

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();
        await page.getByRole('link', { name: ' Public ' }).click();
        await page.getByRole('link', { name: ' Slicer CLI Web Test' }).click();

        await expect(page.getByRole('button', { name: 'Run Task' })).toBeVisible();
        await expect(page.locator('.s-panel-title-container').first()).toBeVisible();

        // A panel can be collapsed and expanded.
        await expect(page.locator('#file1')).toBeVisible();
        await page.locator('.s-panel-title').first().click();
        await expect(page.locator('#file1')).toBeHidden();
        await page.locator('.s-panel-title').first().click();
        await expect(page.locator('#file1')).toBeVisible();
    });
});
