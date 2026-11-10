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
    await expect(page.locator('.g-usage-child .g-usage-open')).toHaveAttribute('href', /^#user\//);
    await expect(page.locator('.g-usage-child .g-usage-open')).toHaveAttribute(
      'title', 'Open this user');
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
    await expect(page.locator('.g-usage-child .g-usage-open')).toHaveAttribute('href', /^#folder\//);

    // Drill into the folder by clicking the treemap
    await page.locator('.g-usage-treemap .apexcharts-treemap-rect').first().click();
    await expect(page.locator('.g-usage-breadcrumbs li.active')).toHaveText('Private');
    await expect(page.locator('.g-usage-child').first()).toContainText('ten_byte_file.txt');
    await expect(page.locator('.g-usage-child').first()).toContainText('Item');
    const itemLink = await page.locator('.g-usage-child .g-usage-open').getAttribute('href');
    expect(itemLink).toMatch(/^#item\//);

    // Drill into the item to see its files
    await page.locator('.g-usage-children a.g-usage-drill', { hasText: 'ten_byte_file.txt' }).click();
    await expect(page.locator('.g-usage-breadcrumbs li')).toHaveCount(4);
    await expect(page.locator('.g-usage-child').first()).toContainText('File');
    await expect(page.locator('.g-usage-children a.g-usage-drill')).toHaveCount(0);
    // A file links to its item
    await expect(page.locator('.g-usage-child .g-usage-open')).toHaveAttribute('href', itemLink);
    await expect(page.locator('.g-usage-child .g-usage-open')).toHaveAttribute(
      'title', 'Open the item of this file');

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

    // Open a resource from the table
    await page.locator('#g-usage-source').selectOption('all');
    await page.locator('.g-usage-child .g-usage-open').first().click();
    await expect(page.locator('.g-user-name')).toHaveText('Admin Admin');
    await waitForIdlePage(page);
  });

  test('Show usage of all assetstores', async ({ page }) => {
    await login(page, 'admin', 'adminpassword!');
    await page.goto(page.url().split('#')[0] + '#assetstores');
    await expect(page.locator('.g-usage-all-link')).toBeVisible();
    await expect(page.locator('.g-usage-all-link')).toHaveText(/^\s*Usage\s*$/);
    // The button follows the button of the import tracker plugin
    await expect(page.locator('.g-view-imports + .g-usage-all-link')).toBeVisible();
    await page.locator('.g-usage-all-link').click();
    await expect(page.locator('#g-usage-assetstore')).toHaveValue('');
    await expect(page.locator('.g-usage-child').first()).toContainText('admin');
    await expect(page.locator('.g-usage-computed')).toContainText('Totals computed');

    // Recompute the totals
    await page.locator('.g-usage-refresh').click();
    await expect(page.locator('.g-usage-child').first()).toContainText('admin');
  });

  test('Summarize children past the limit', async ({ page }) => {
    await login(page, 'admin', 'adminpassword!');
    await page.locator('#g-app-header-container').getByText('admin').click();
    await page.locator('a.g-my-folders').click();
    await page.getByRole('link', { name: ' Public ' }).click();
    await upload(page, path.join(__dirname, 'data', 'testFile.txt'));

    // List only the largest child, so the other folder is summarized
    await page.route('**/api/v1/assetstore/usage?*', (route) => route.continue({
      url: route.request().url().replace(/([?&]limit=)\d+/, '$11')
    }));
    await page.goto(page.url().split('#')[0] + '#assetstores/usage');
    // Include the new file in the cached totals
    await page.locator('.g-usage-refresh').click();
    await expect(page.locator('.g-usage-total-size')).toHaveText(/16 B/);
    await page.locator('.g-usage-children a.g-usage-drill', { hasText: 'admin' }).click();
    await expect(page.locator('.g-usage-breadcrumbs li.active')).toHaveText('admin');
    await expect(page.locator('.g-usage-child')).toHaveCount(1);
    await expect(page.locator('.g-usage-other td').first()).toHaveText('1 more folder');
    await expect(page.locator('.g-usage-treemap .apexcharts-treemap-rect')).toHaveCount(2);
    await expect(page.locator('.g-usage-treemap')).toContainText('1 more folder');
    await page.unrouteAll();

    // Attached files link to the resource they are attached to.  Files can't
    // be attached from the web client, so add them to the response.
    await page.route('**/api/v1/assetstore/usage?*', async (route) => {
      const response = await route.fetch();
      const usage = await response.json();
      usage.children.push({
        type: 'attached', _id: null, name: 'Attached files', size: 5, count: 1, drillable: false
      });
      await route.fulfill({ response, json: usage });
    });
    await page.locator('.g-usage-children a.g-usage-drill').first().click();
    const attached = page.locator('.g-usage-child[g-type="attached"]');
    await expect(attached).toContainText('Attached files');
    await expect(attached.locator('.g-usage-open')).toHaveAttribute('href', /^#folder\//);
    await expect(attached.locator('.g-usage-open')).toHaveAttribute(
      'title', 'Open the folder these files are attached to');
    await attached.locator('.g-usage-open').click();
    await expect(page.locator('.g-hierarchy-widget')).toBeVisible();
    await page.unrouteAll();
  });

  test('Non-admins cannot see storage usage', async ({ page }) => {
    await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
    await page.goto(page.url().split('#')[0] + '#assetstores/usage');
    await expect(page.getByText('Must be logged in as admin to view this page.')).toBeVisible();
  });
});
