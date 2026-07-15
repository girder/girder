import { expect, test } from '@playwright/test';

import { createUser, delay, login, logout, waitForDialog } from '../util';
import { setupServer } from '../server';

test.describe('Create an admin and non-admin user', () => {
  setupServer();

  test('Register a user (first is admin)', async ({ page }) => {
    await expect(page.getByText('Admin console')).toBeHidden();
    await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
    await expect(page.getByText('Admin console')).toBeVisible();
    await logout(page);
    await expect(page.getByText('Admin console')).toBeHidden();
  });

  test('Register a second user (non-admin)', async ({ page }) => {
    await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
    await delay(1000);
    await expect(page.getByText('Admin console')).toBeHidden();
    await logout(page);
  });

  test('Login non-admin user', async ({ page }) => {
    await login(page, 'johndoe', 'password!');
    await logout(page);
  });

  test('Create public group', async ({ page }) => {
    await login(page, 'johndoe', 'password!');
    await page.getByText('Groups').click();
    await page.getByRole('button', { name: ' Create Group' }).click();
    await waitForDialog(page);
    await page.getByText('Public — Anyone can see this group').click();
    await page.getByLabel('Name').fill('pubGroup', { timeout: 1000 });
    await page.getByLabel('Description (optional)').fill('public group', { timeout: 1000 });
    await page.getByRole('button', { name: ' Create', exact: true }).click();
  });
});

test.describe('Test the plugins page', () => {
  setupServer();

  test('Login as admin, view plugins page and logout', async ({ page }) => {
    // First create an admin user (first registered user is admin)
    await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
    // Navigate to plugins page via Admin console menu
    await page.getByRole('link', { name: ' Admin console' }).click();
    await page.getByRole('link', { name: ' Plugins' }).click();
    // Wait for the plugin list to load - at least core plugins should be present
    await expect(page.locator('.g-plugin-list-container')).toBeVisible({ timeout: 10000 });
    // Check that there is at least one plugin (core plugins should always be present)
    const pluginCount = await page.locator('.g-plugin-list-item').count();
    expect(pluginCount).toBeGreaterThanOrEqual(1);
    // Verify we can see some plugins listed
    const pluginList = page.locator('.g-plugin-list-item');
    await expect(pluginList.first()).toBeVisible();
    // Logout via user dropdown (visible on the admin/plugins page)
    await page.locator('.g-user-dropdown-link').click();
    await page.locator('.g-logout').click();
    await expect(page.locator('.g-register')).toBeVisible();
    await expect(page.locator('.g-login')).toBeVisible();
  });
});
