import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the show download setting', () => {
  setupServer();

  test('hides the item download button when core.show_download is none', async ({ page }) => {
    await createUser(page, 'admin');

    await page.locator('#g-app-header-container').getByText('admin').click();
    await page.locator('a.g-my-folders').click();
    await page.getByRole('link', { name: 'Private' }).click();

    await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'));
    await page.getByRole('link', { name: 'ten_byte_file.txt' }).click();

    await page.getByRole('button', { name: 'Actions' }).click();
    await expect(page.locator('.g-download-item')).toBeVisible();

    const girderToken = await page.evaluate(() => window.localStorage.getItem('girderToken'));
    const resp = await page.request.put(new URL('/api/v1/system/setting', page.url()).toString(), {
      headers: { 'Girder-Token': girderToken! },
      form: { key: 'core.show_download', value: 'none' },
    });
    expect(resp.ok()).toBeTruthy();

    await page.reload();
    await page.getByRole('button', { name: 'Actions' }).click();
    await expect(page.locator('.g-download-item')).toBeHidden();
  });
});
