import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the quota front-end', () => {
    setupServer();

    test('exercise quota administration and enforcement', async ({ page }) => {
        await createUser(page, 'admin');

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.getByRole('link', { name: ' My folders' }).click();

        await page.getByRole('button', { name: ' Actions ' }).click();
        await page.getByRole('menuitem', { name: ' Quota and assetstore policies' }).click();
        await page.getByPlaceholder('Maximum allowed size of all files, or blank for no limit').fill('15');
        await page.getByRole('button', { name: ' Save' }).click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();

        await page.getByRole('link', { name: ' Private ' }).click();

        // Uploading 10B should succeed
        await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'));

        // Uploading 10 more bytes should fail due to exceeding quota
        await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'), false);

        await expect(page.getByText('Error: Upload would exceed file storage quota (need 10 B, only 5 B available')).toBeVisible();
    });
});
