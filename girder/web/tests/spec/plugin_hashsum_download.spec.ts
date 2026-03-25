import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the hashsum download front-end', () => {
    setupServer();

    test('verify presence of key file', async ({ page }) => {
        await createUser(page, 'admin');
        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.getByRole('link', { name: ' My folders' }).click();
        await page.getByRole('link', { name: ' Private ' }).click();
        await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'));

        await page.getByRole('link', { name: ' ten_byte_file.txt' }).click();
        await page.getByTitle('Show info').click();
        await expect(page.locator('input.g-hash-textbox').first()).toHaveValue('ff3245abe317049ed1b8aa7aa2f4c4dcb8bf86f083ed67eb26b43e2fbe3ba8fdf759f9e2f46fcf2a06c2dfeddf0cedcd41a68034cd618b880785b34f759d1a69')
    });
});
