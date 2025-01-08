import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function asyncRestRequest(page, opts) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            window.girder.rest.restRequest(opts).done((resp) => {
                resolve(resp);
            }).fail((resp) => {
                reject(resp);
            });
        });
    }, opts);
}

async function createCliItem(page) {
    const resp = await asyncRestRequest(page, {
        url: '/folder',
        data: {
            text: 'Public',
            limit: 1,
        }
    });
    const folderId = resp[0]._id;
    const data = fs.readFileSync(path.join(__dirname, 'data', 'slicer_cli_web_test.xml'));
    const base64data = Buffer.from(data).toString('base64');

    await asyncRestRequest(page, {
        url: '/slicer_cli_web/cli',
        method: 'POST',
        data: {
            folder: folderId,
            image: 'girder/slicer_cli_web_test:latest',
            name: 'Slicer CLI Web Test',
            desc_type: 'xml',
            spec: base64data,
            replace: false,
        },
    });
};

test.describe('Test Slicer CLI web', () => {
    setupServer();

    test('create a CLI item', async ({ page }) => {
        await createUser(page, 'admin');
        await createCliItem(page);

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.getByRole('link', { name: ' My folders' }).click();
        await page.getByRole('link', { name: ' Public ' }).click();
        await page.getByRole('link', { name: ' Slicer CLI Web Test' }).click();
        await expect(page.getByRole('button', { name: 'Run Task' })).toBeVisible();
        await expect(page.getByText('An input file', { exact: true })).toBeVisible();
        await expect(page.getByText('An input image', { exact: true })).toBeVisible();
        await expect(page.getByText('An input item', { exact: true })).toBeVisible();
    });
});
