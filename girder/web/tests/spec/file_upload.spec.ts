import path from 'path';
import { fileURLToPath } from 'url';

import { test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test file endpoints from the front-end', () => {
    setupServer();

    test('file upload uses default mime type when none provided', async ({ page }) => {
        await createUser(page, 'admin');
        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();
        await page.getByRole('link', { name: ' Private ' }).click();
        await upload(page, path.join(__dirname, 'data', 'nomime.dat'));
    });
});
