import path from 'path';
import { fileURLToPath } from 'url';

import { Locator, Page, expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, login, waitForDialog, waitForIdlePage } from '../util';

/**
 * Ported from 3.x-maintenance:
 * plugins/item_licenses/plugin_tests/itemLicensesSpec.js
 *
 * Tests the item_licenses plugin: selecting a license when creating/editing an
 * item or uploading a file, viewing the license on the item page, and the
 * behavior of the "Unspecified" license.
 *
 * The original spec was a single sequential Jasmine describe. This port keeps
 * the same sequence in a serial Playwright describe: the server and database
 * are shared across the whole describe, admin is registered in the first test,
 * and later tests log back in as needed.
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ADMIN = {
    login: 'admin',
    email: 'admin@girder.test',
    firstName: 'Admin',
    lastName: 'User',
    password: 'password!',
};

const MIT_LICENSE = 'The MIT License (MIT)';
const APACHE_LICENSE = 'Apache License 2';

/** The number of license options: 12 code + 9 content, plus "Unspecified". */
const NUM_LICENSES = 22;

/**
 * Navigate to the admin's folder list.
 */
async function gotoMyFolders(page: Page) {
    await expect(page.locator('.g-user-dropdown-link')).toBeVisible();
    await page.locator('.g-user-dropdown-link').click();
    await page.locator('a.g-my-folders').click();
    await expect(page.locator('a.g-folder-list-link', { hasText: 'Public' })).toBeVisible();
}

/**
 * Open a folder of the current user's page by name.
 */
async function openFolder(page: Page, name: string) {
    await expect(page.locator('a.g-folder-list-link', { hasText: name })).toBeVisible();
    await page.locator('a.g-folder-list-link', { hasText: name }).click();
    await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
    await waitForIdlePage(page);
}

/**
 * Assert that the license select in the currently open dialog has the expected
 * options and selected value.
 */
async function expectLicenseSelect(select: Locator, currentLicense: string) {
    await expect(select).toBeVisible();
    await expect(select.locator('optgroup')).toHaveCount(2);
    await expect(select.locator('option')).toHaveCount(NUM_LICENSES);
    await expect(select).toHaveValue(currentLicense);
}

/**
 * Open the "Create item here" dialog from the folder actions menu.
 */
async function openCreateItemDialog(page: Page) {
    await page.locator('.g-folder-actions-button:visible').click();
    await expect(page.locator('a.g-create-item:visible')).toHaveCount(1);
    await page.locator('a.g-create-item:visible').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=itemcreate');
    await waitForDialog(page);
    await expect(page.locator('.g-save-item:visible')).toHaveText('Create');
}

/**
 * Open the item edit dialog from the item actions menu.
 */
async function openEditItemDialog(page: Page) {
    await expect(page.locator('.g-item-actions-button:visible')).toHaveCount(1);
    await page.locator('.g-item-actions-button:visible').click();
    await expect(page.locator('.g-edit-item:visible')).toHaveCount(1);
    await page.locator('.g-edit-item:visible').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=itemedit');
    await waitForDialog(page);
    await expect(page.locator('#g-name')).not.toHaveValue('');
    await expect(page.locator('.g-save-item:visible')).toHaveText('Save');
}

/**
 * Open an item from the current folder listing and return once the item page's
 * license field has loaded.
 */
async function openItem(page: Page, name: string) {
    await expect(page.locator('a.g-item-list-link', { hasText: name })).toHaveCount(1);
    await page.locator('a.g-item-list-link', { hasText: name }).click();
    await expect(page.locator('.g-item-name')).toHaveText(name);
    await expect(page.locator('.g-item-license')).toHaveCount(1);
    await waitForIdlePage(page);
}

/**
 * Navigate back to the Public folder listing via the breadcrumb.
 */
async function backToPublicFolder(page: Page) {
    await expect(page.locator('a.g-item-breadcrumb-link', { hasText: 'Public' })).toBeVisible();
    await page.locator('a.g-item-breadcrumb-link', { hasText: 'Public' }).click();
    await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
    await waitForIdlePage(page);
}

test.describe('Test the item licenses front-end', () => {
    setupServer();

    test('register the admin user', async ({ page }) => {
        await createUser(page, ADMIN.login, ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);
    });

    test('create an item with a license', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoMyFolders(page);
        await openFolder(page, 'Public');
        await openCreateItemDialog(page);

        // "Unspecified" is selected by default.
        await expectLicenseSelect(page.locator('#g-license'), '');

        await page.locator('input#g-name').fill('Test Item');
        await page.locator('#g-license').selectOption(MIT_LICENSE);
        await page.locator('.g-save-item').click();
        await waitForIdlePage(page);

        await openItem(page, 'Test Item');
        await expect(page.locator('.g-item-license')).toContainText(MIT_LICENSE);
    });

    test('edit an item license', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoMyFolders(page);
        await openFolder(page, 'Public');
        await openItem(page, 'Test Item');

        await openEditItemDialog(page);
        // The item's current license is selected by default.
        await expectLicenseSelect(page.locator('#g-license'), MIT_LICENSE);

        await page.locator('#g-license').selectOption(APACHE_LICENSE);
        await page.locator('.g-save-item').click();
        await waitForIdlePage(page);

        await expect(page.locator('.g-item-license')).toContainText(APACHE_LICENSE);
    });

    test('upload into an item does not show the license widget', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoMyFolders(page);
        await openFolder(page, 'Public');
        await openItem(page, 'Test Item');

        await expect(page.locator('.g-upload-into-item:visible')).toHaveCount(1);
        await page.locator('.g-upload-into-item:visible').click();
        await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=upload');
        await waitForDialog(page);
        await expect(page.locator('.g-start-upload:visible')).toContainText('Start Upload');

        // Uploading into a specific item must not offer a license selection.
        await expect(page.locator('#g-license')).toHaveCount(0);

        // Close the dialog and return to the folder listing.
        await page.locator('#g-dialog-container .modal-header .close').click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();
        await backToPublicFolder(page);
    });

    test('upload a file into a folder, specifying a license', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoMyFolders(page);
        await openFolder(page, 'Public');

        await page.locator('.g-upload-here-button:visible').click();
        await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=upload');
        await waitForDialog(page);
        await expect(page.locator('.g-start-upload:visible')).toContainText('Start Upload');

        // Uploading into a folder offers the license selection widget.
        await expectLicenseSelect(page.locator('#g-license'), '');
        await page.locator('#g-license').selectOption(APACHE_LICENSE);

        await page.locator('#g-files').setInputFiles(path.join(__dirname, 'data', 'testFile.txt'));
        await expect(page.locator('.g-start-upload')).toBeEnabled();
        await page.locator('.g-start-upload').click();
        await waitForIdlePage(page);
        await expect(page.locator('#g-dialog-container')).toBeHidden();

        await openItem(page, 'testFile.txt');
        await expect(page.locator('.g-item-license')).toContainText(APACHE_LICENSE);

        await backToPublicFolder(page);
    });

    test('create an item with an unspecified license', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoMyFolders(page);
        await openFolder(page, 'Public');
        await openCreateItemDialog(page);

        await expectLicenseSelect(page.locator('#g-license'), '');

        await page.locator('input#g-name').fill('Test Item 2');
        await page.locator('#g-license').selectOption('');
        await page.locator('.g-save-item').click();
        await waitForIdlePage(page);

        await openItem(page, 'Test Item 2');
        await expect(page.locator('.g-item-license')).toContainText('Unspecified');
    });

    test('edit an item that has an unspecified license', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoMyFolders(page);
        await openFolder(page, 'Public');
        await openItem(page, 'Test Item 2');

        await openEditItemDialog(page);
        // The unspecified license is selected by default.
        await expectLicenseSelect(page.locator('#g-license'), '');

        await page.locator('#g-license').selectOption(MIT_LICENSE);
        await page.locator('.g-save-item').click();
        await waitForIdlePage(page);

        await expect(page.locator('.g-item-license')).toContainText(MIT_LICENSE);
    });

    test('edit an item to have an unspecified license', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoMyFolders(page);
        await openFolder(page, 'Public');
        await openItem(page, 'Test Item 2');

        await openEditItemDialog(page);
        await expectLicenseSelect(page.locator('#g-license'), MIT_LICENSE);

        await page.locator('#g-license').selectOption('');
        await page.locator('.g-save-item').click();
        await waitForIdlePage(page);

        await expect(page.locator('.g-item-license')).toContainText('Unspecified');
    });
});
