import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the readme UI', () => {
    setupServer();

    test('render a README.md file', async ({ page }) => {
        await createUser(page, 'myuser');

        await page.locator('#g-app-header-container').getByText('myuser').click();
        await page.getByRole('link', { name: ' My folders' }).click();
        await page.getByRole('link', { name: ' Public ' }).click();
        await upload(page, path.join(__dirname, 'data', 'README.md'));
        await expect(page.locator('h1', {hasText: 'README Testing'})).toBeVisible();
    });
});
