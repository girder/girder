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
        await page.getByRole('link', { name: ' My folders' }).click();
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
