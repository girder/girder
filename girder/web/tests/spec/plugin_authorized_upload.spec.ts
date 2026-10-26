import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, logout } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the authorized upload front-end', () => {
    setupServer();

    test('exercise authorized upload', async ({ page }) => {
        await createUser(page, 'admin');

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();
        await page.getByRole('link', { name: ' Private ' }).click();
        await page.getByRole('button', { name: ' ' }).click();
        await page.getByRole('link', { name: ' Authorize upload here' }).click();

        await page.getByText('Generate URL').click();
        await expect(page.locator('.g-authorized-upload-url-target')).toHaveValue(/.*#authorized_upload\/[a-f0-9]+\/[a-zA-Z0-9]/);

        const authorizedUrl = await page.locator('.g-authorized-upload-url-target').inputValue();

        await logout(page);

        await page.goto(authorizedUrl);

        await page.locator('#g-files').setInputFiles(path.join(__dirname, 'data', 'ten_byte_file.txt'));
        await page.getByRole('button', { name: ' Start Upload' }).click();
        await expect(page.getByText('Thank you! Your file has been received.')).toBeVisible();
    });

});

test.describe('Test the authorized upload menu entry in the htk style', () => {
    setupServer();

    test('the entry is inside the folder actions menu', async ({ page }) => {
        await createUser(page, 'admin');
        const girderToken = await page.evaluate(() => window.localStorage.getItem('girderToken'));
        const resp = await page.request.put(new URL('/api/v1/system/setting', page.url()).toString(), {
            headers: { 'Girder-Token': girderToken! },
            form: { key: 'core.ui_style', value: 'htk' },
        });
        expect(resp.ok()).toBeTruthy();
        await page.reload();
        await expect(page.locator('html')).toHaveClass(/g-ui-htk/);

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();
        await page.locator('a.g-folder-list-link', { hasText: 'Private' }).click();
        await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
        await expect(page.locator('.g-folder-actions-menu a.g-authorize-upload-here')).toHaveCount(1);
        await expect(page.locator('.g-authorize-upload-here')).toBeHidden();
        await page.locator('.g-folder-actions-button:visible').click();
        await expect(page.locator('.g-folder-actions-menu a.g-authorize-upload-here')).toBeVisible();
        await page.locator('.g-folder-actions-menu a.g-authorize-upload-here').click();
        await expect(page.getByText('Generate URL')).toBeVisible();
    });
});
