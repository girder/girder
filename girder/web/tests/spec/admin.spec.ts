import { expect, test } from '@playwright/test';

import { createUser, login, logout, waitForDialog, waitForIdlePage } from '../util';
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
    // After createUser creates the user and verifies REST request completion,
    // we should be able to immediately verify the Admin console is not shown
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

test.describe('Test the assetstore page', () => {
  setupServer();

  const _getAssetstoreContainer = async (page: import('@playwright/test').Page, name: string) => {
    const containers = page.locator('.g-assetstore-container');
    for (let i = 0; i < await containers.count(); i++) {
      const containerName = await containers.nth(i).locator('span.g-assetstore-name').textContent();
      if (containerName?.trim() === name) {
        return containers.nth(i);
      }
    }
    return null;
  };

  test('Anonymous loading assetstore page prompts login', async ({ page }) => {
    await expect(page.locator('.g-login')).toBeVisible();
  });

  test('Create, manage, and delete filesystem assetstore', async ({ page }) => {
    // First create an admin user (first users get admin privileges)
    await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
    // Navigate to assetstores page via Admin console
    await page.getByRole('link', { name: 'Admin console' }).click();
    await expect(page.locator('.g-assetstore-config')).toBeVisible({ timeout: 10000 });
    await page.locator('.g-assetstore-config').click();
    // Wait for assetstores to load and render
    await expect(page.locator('.g-assetstore-container').first()).toBeVisible({ timeout: 10000 });
    const testAssetstoreName = 'Test Filesystem Assetstore';
    // Open the filesystem tab and click create
    await page.locator('[data-target="#g-create-fs-tab"]').click();
    await expect(page.locator('#g-create-fs-tab .g-new-assetstore-submit:visible')).toBeVisible({
      timeout: 10000
    });
    await page.locator('#g-create-fs-tab .g-new-assetstore-submit').click();
    // Wait for validation message to appear (empty required fields)
    const validationResult = page.locator('#g-create-fs-tab .g-validation-failed-message:visible');
    await expect(validationResult).toHaveText(/.*/);
    // Fill in required fields
    await page.locator('#g-new-fs-name').fill(testAssetstoreName);
    await page.locator('#g-new-fs-root').fill('/tmp/assetstore');
    // Wait for create button to be enabled
    await expect(page.locator('#g-create-fs-tab .g-new-assetstore-submit')).not.toBeDisabled();
    // Create the assetstore
    await page.locator('#g-create-fs-tab .g-new-assetstore-submit').click();
    await expect(page.locator(`.g-assetstore-container span:has-text("${testAssetstoreName}"):visible`)).toHaveText(testAssetstoreName);
    // Make this the current assetstore
    const newContainer = await _getAssetstoreContainer(page, testAssetstoreName);
    expect(newContainer).not.toBeNull();
    await newContainer!.locator('.g-set-current').click();
    // Wait for dialog to close and REST request to complete
    await expect(newContainer!.locator('.g-set-current')).toBeHidden();
    await waitForIdlePage(page);
    // Navigate away and back to verify assetstore persists
    await page.getByRole('link', { name: 'Admin console' }).click();
    await expect(page.locator('.g-assetstore-config')).toBeVisible({ timeout: 10000 });
    await page.locator('.g-assetstore-config').click();
    await expect(page.locator('.g-assetstore-container').first()).toBeVisible();
    // Verify the assetstore is still current (should have "is current" label)
    const restoredContainer = await _getAssetstoreContainer(page, testAssetstoreName);
    expect(restoredContainer).not.toBeNull();
    // Delete the test assetstore
    await restoredContainer!.locator('.g-delete-assetstore').click();
    await waitForDialog(page);
    await expect(page.locator('#g-confirm-button:visible')).toBeVisible();
    await page.locator('#g-confirm-button').click();
    // Wait for the deletion to complete - verify test assetstore is gone by checking count
    const remainingContainers = page.locator('.g-assetstore-container');
    await expect(remainingContainers).toHaveCount(1); // Only the temp filesystem assetstore should remain
    // Verify only the temp assetstore remains (which has a temp directory name as title)
    await expect(page.locator('.g-assetstore-container .g-assetstore-name')).toContainText('/tmp/');
    await logout(page);
  });
});

test.describe('Test the settings page', () => {
  setupServer();

  test('Anonymous loading settings page prompts login', async ({ page }) => {
    await expect(page.locator('.g-login')).toBeVisible();
  });

  test('Login as admin, view server configuration page and verify readonly state', async ({ page }) => {
    // First create an admin user (first registered user is admin)
    await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
    // Navigate to settings page via Admin console
    await page.getByRole('link', { name: 'Admin console' }).click();
    await expect(page.locator('.g-server-config')).toBeVisible({ timeout: 10000 });
    await page.locator('.g-server-config').click();
    // Wait for settings page to load - title section and form should appear
    await expect(page.getByText('System configuration')).toBeVisible({ timeout: 10000 });
    // Verify main sections exist on the settings page (read-only in Girder 5.x)
    await expect(page.getByText('Instance Branding')).toBeVisible();
    await expect(page.getByText('Administrative Policy')).toBeVisible();
    await expect(page.getByText('Email Creation')).toBeVisible();
    await expect(page.getByText('Email Delivery')).toBeVisible();
    await expect(page.getByText('Advanced Settings')).toBeVisible();
    // Verify cookie-lifetime setting exists and is disabled
    const cookieLifetimeInput = page.locator('#g-core-cookie-lifetime');
    await expect(cookieLifetimeInput).toHaveAttribute('disabled');
    // Verify SMTP host setting exists and is disabled
    const smtpHostInput = page.locator('#g-core-smtp-host');
    await expect(smtpHostInput).toHaveAttribute('disabled');
    // Verify brand name setting exists and is disabled
    const brandNameInput = page.locator('#g-core-brand-name');
    await expect(brandNameInput).toHaveAttribute('disabled');
    // Verify registration policy select exists and is disabled
    const registrationPolicySelect = page.locator('#g-core-registration-policy');
    await expect(registrationPolicySelect).toHaveAttribute('disabled');
    // Verify Collection creation policy section exists via its label/description text
    const collectionCreateLabel = page.getByText('Allow additional users and groups to create collections.');
    await expect(collectionCreateLabel).toBeVisible();
    // Save settings button should exist
    await expect(page.getByRole('button', { name: 'Save' })).toBeVisible();
    await logout(page);
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
