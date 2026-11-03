import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, login, upload, waitForIdlePage } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the storage usage page', () => {
  setupServer();

  test('Drill down into storage usage', async ({ page }) => {
    await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
    await page.locator('#g-app-header-container').getByText('admin').click();
    await page.locator('a.g-my-folders').click();
    await page.getByRole('link', { name: ' Private ' }).click();
    await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'));

    // Open the usage page for the assetstore from the assetstores page
    await page.getByText('Admin console').click();
    await page.locator('.g-assetstore-config').click();
    await expect(page.locator('.g-assetstore-container').first()).toBeVisible();
    await page.locator('.g-assetstore-usage').first().click();
    await expect(page.locator('.g-usage-children')).toBeVisible();
    await expect(page.locator('.g-usage-total-size')).toHaveText(/10 B/);
    await expect(page.locator('.g-usage-child')).toHaveCount(1);
    await expect(page.locator('.g-usage-child').first()).toContainText('admin');
    await expect(page.locator('.g-usage-child').first()).toContainText('User');
    await expect(page.locator('.g-usage-treemap svg.apexcharts-svg')).toBeVisible();
    await expect(page.locator('.g-usage-top-file')).toHaveCount(1);
    await expect(page.locator('.g-usage-top-file')).toContainText('ten_byte_file.txt');
    await expect(page.locator('.g-usage-top-file .g-usage-file-resource')).toHaveAttribute(
      'href', /^#item\//);
    await expect(page.locator('.g-usage-top-file .g-usage-file-resource')).toHaveText(
      '/user/admin/Private/ten_byte_file.txt');
    await expect(page.locator('.g-usage-top-file .g-usage-file-resource')).toHaveAttribute(
      'title', '/user/admin/Private/ten_byte_file.txt');

    // Drill into the user from the table
    await page.locator('.g-usage-children a.g-usage-drill', { hasText: 'admin' }).click();
    await expect(page.locator('.g-usage-breadcrumbs li.active')).toHaveText('admin');
    await expect(page.locator('.g-usage-child')).toHaveCount(1);
    await expect(page.locator('.g-usage-child').first()).toContainText('Private');

    // Drill into the folder by clicking the treemap
    await page.locator('.g-usage-treemap .apexcharts-treemap-rect').first().click();
    await expect(page.locator('.g-usage-breadcrumbs li.active')).toHaveText('Private');
    await expect(page.locator('.g-usage-child').first()).toContainText('ten_byte_file.txt');
    await expect(page.locator('.g-usage-child').first()).toContainText('Item');

    // Drill into the item to see its files
    await page.locator('.g-usage-children a.g-usage-drill', { hasText: 'ten_byte_file.txt' }).click();
    await expect(page.locator('.g-usage-breadcrumbs li')).toHaveCount(4);
    await expect(page.locator('.g-usage-child').first()).toContainText('File');
    await expect(page.locator('.g-usage-children a.g-usage-drill')).toHaveCount(0);

    // Changing options keeps the current resource
    await page.locator('#g-usage-dedup').check();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dedup=true');
    await expect(page.locator('.g-usage-child')).toHaveCount(1);
    await page.locator('#g-usage-source').selectOption('imported');
    await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('source=imported');
    await expect(page.locator('.g-usage-empty')).toBeVisible();

    // Return to the top level with the breadcrumb
    await page.locator('.g-usage-breadcrumbs a.g-usage-drill').first().click();
    await expect(page.locator('.g-usage-breadcrumbs li.active')).toHaveText('All users and collections');
    await expect(page.locator('#g-usage-source')).toHaveValue('imported');
    await expect(page.locator('#g-usage-dedup')).toBeChecked();
    await waitForIdlePage(page);
  });

  test('Show usage of all assetstores', async ({ page }) => {
    await login(page, 'admin', 'adminpassword!');
    await page.goto(page.url().split('#')[0] + '#assetstores');
    await expect(page.locator('.g-usage-all-link')).toBeVisible();
    await page.locator('.g-usage-all-link').click();
    await expect(page.locator('#g-usage-assetstore')).toHaveValue('');
    await expect(page.locator('.g-usage-child').first()).toContainText('admin');
    await expect(page.locator('.g-usage-computed')).toContainText('Totals computed');

    // Recompute the totals
    await page.locator('.g-usage-refresh').click();
    await expect(page.locator('.g-usage-child').first()).toContainText('admin');
  });

  test('Non-admins cannot see storage usage', async ({ page }) => {
    await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
    await page.goto(page.url().split('#')[0] + '#assetstores/usage');
    await expect(page.getByText('Must be logged in as admin to view this page.')).toBeVisible();
  });
});
