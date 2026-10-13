import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, waitForIdlePage } from '../util';

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

async function createCliItem(page, { specFile = 'slicer_cli_web_test.xml', name = 'Slicer CLI Web Test' } = {}) {
    const resp = await asyncRestRequest(page, {
        url: '/folder',
        data: {
            text: 'Public',
            limit: 1,
        }
    });
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
};

test.describe('Test Slicer CLI web', () => {
    setupServer();

    test('create a CLI item', async ({ page }) => {
        await createUser(page, 'admin');
        await createCliItem(page);
        // Wait for all REST requests from CLI creation to complete before navigating
        await waitForIdlePage(page);

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();
        await page.getByRole('link', { name: ' Public ' }).click();
        await page.getByRole('link', { name: ' Slicer CLI Web Test' }).click();
        await expect(page.getByRole('button', { name: 'Run Task' })).toBeVisible();
        await expect(page.getByText('An input file', { exact: true })).toBeVisible();
        await expect(page.getByText('An input image', { exact: true })).toBeVisible();
        await expect(page.getByText('An input item', { exact: true })).toBeVisible();
    });
});

test.describe('Test a multiple Slicer CLI web input', () => {
    setupServer();

    test('render a multiple input without the batch file picker', async ({ page }) => {
        await createUser(page, 'admin');
        await createCliItem(page, {
            specFile: 'slicer_cli_web_multiple_test.xml',
            name: 'Slicer CLI Web Multiple Test',
        });
        await waitForIdlePage(page);

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();
        await page.getByRole('link', { name: ' Public ' }).click();
        await page.getByRole('link', { name: ' Slicer CLI Web Multiple Test' }).click();
        await expect(page.getByRole('button', { name: 'Run Task' })).toBeVisible();
        await expect(page.getByText('Input series', { exact: true })).toBeVisible();
        await expect(page.getByText('Single input file', { exact: true })).toBeVisible();

        // A multiple input still offers the single-file picker, but batch mode
        // (the multi-file picker) is not available for it.
        const multipleItem = page.locator('.s-control-item[data-control-id="inputSeries"]');
        await expect(multipleItem.locator('.s-select-file-button')).toBeVisible();
        await expect(multipleItem.locator('.s-select-multifile-button')).toBeHidden();

        // A normal file input is unchanged and still offers the multi-file picker.
        const singleItem = page.locator('.s-control-item[data-control-id="singleFile"]');
        await expect(singleItem.locator('.s-select-file-button')).toBeVisible();
        await expect(singleItem.locator('.s-select-multifile-button')).toBeVisible();
    });
});
