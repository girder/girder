import path from 'path';
import { fileURLToPath } from 'url';

import { Page, expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, login, logout, upload, waitForDialog, waitForIdlePage } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the quota front-end', () => {
    setupServer();

    test('exercise quota administration and enforcement', async ({ page }) => {
        await createUser(page, 'admin');

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();

        await page.getByRole('button', { name: ' Actions ' }).click();
        await page.getByRole('menuitem', { name: ' Quota and assetstore policies' }).click();
        await page.getByPlaceholder('Maximum allowed size of all files, or blank for no limit').fill('15');
        await page.getByRole('button', { name: ' Save' }).click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();
        // Wait for quota setting to be saved via REST before proceeding
        await waitForIdlePage(page);

        await page.getByRole('link', { name: ' Private ' }).click();

        // Uploading 10B should succeed
        await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'));

        // Uploading 10 more bytes should fail due to exceeding quota
        await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'), false);

        await expect(page.getByText('Error: Upload would exceed file storage quota (need 10 B, only 5 B available')).toBeVisible();
    });
});

/**
 * Ported from 3.x-maintenance: plugins/user_quota/plugin_tests/userQuotaSpec.js
 *
 * The original spec was a single sequential Jasmine describe that exercised
 * the whole plugin: it registered an admin plus three normal users, created a
 * couple of collections, made them public and shared them with user1, set the
 * default user/collection quotas through the plugin config page, set per
 * resource quotas through the "Quota and assetstore policies" dialog, checked
 * quota enforcement on upload, verified which users may see the dialog, and
 * checked that resources which never had a quota set fall back to the default.
 *
 * The port keeps that sequence in a serial Playwright describe so the server
 * and database are shared just like the original. Each Playwright test gets a
 * fresh browser context, so no explicit logout is needed at the start of a
 * test; logins are performed as required.
 */

const ADMIN = {
    login: 'admin',
    email: 'admin@girder.test',
    firstName: 'Quota',
    lastName: 'Admin',
    password: 'testpassword',
};

const USER1 = {
    login: 'user1',
    email: 'user@girder.test',
    firstName: 'Quota',
    lastName: 'User',
    password: 'testpassword',
};

const USER2 = {
    login: 'user2',
    email: 'user2@girder.test',
    firstName: 'Another',
    lastName: 'User',
    password: 'testpassword',
};

const USER3 = {
    login: 'user3',
    email: 'user3@girder.test',
    firstName: 'Third',
    lastName: 'User',
    password: 'testpassword',
};

/** Routes captured while the quota dialogs are open, used by the route test. */
const routes: Record<string, string> = {};

/** Make a REST request from within the page context and await its result. */
async function api(page: Page, opts: Record<string, unknown>) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.rest.restRequest(opts).done((resp: unknown) => {
                resolve(resp);
            }).fail((resp: unknown) => {
                reject(resp);
            });
        });
    }, opts);
}

/** Read a single system setting through the REST API. */
async function getSetting(page: Page, key: string) {
    return await api(page, {
        url: 'system/setting',
        method: 'GET',
        data: { key },
    });
}

/** Navigate in-app without reloading the page (equivalent of testRoute). */
async function navigate(page: Page, route: string) {
    await page.evaluate((r) => {
        // @ts-ignore - window.girder is available at runtime
        window.girder.router.navigate(r.replace(/^#/, ''), { trigger: true });
    }, route);
}

/** Navigate to the collections list page and wait for it to load. */
async function gotoCollectionsPage(page: Page) {
    await page.locator('a.g-nav-link[g-target="collections"]').click();
    await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
    await waitForIdlePage(page);
}

/** Create a collection by name and wait for its page to load. */
async function createCollection(page: Page, name: string) {
    await gotoCollectionsPage(page);
    await page.locator('.g-collection-create-button').click();
    await waitForDialog(page);
    await page.locator('#g-name').fill(name);
    await page.locator('.g-save-collection').click();
    await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText(name);
    await waitForIdlePage(page);
}

/** Navigate to a collection by name and wait for its page to load. */
async function gotoCollection(page: Page, name: string) {
    await gotoCollectionsPage(page);
    await page.locator('a.g-collection-link', { hasText: name }).click();
    await expect(page.locator('.g-collection-actions-button:visible')).toBeVisible();
    await waitForIdlePage(page);
}

/** Navigate to a user page by full name and wait for it to load. */
async function gotoUser(page: Page, fullName: string) {
    await page.locator('a.g-nav-link[g-target="users"]').click();
    await expect(page.locator('a.g-user-link').first()).toBeVisible();
    await page.locator('a.g-user-link', { hasText: fullName }).click();
    await expect(page.locator('.g-user-name')).toHaveText(fullName);
    await waitForIdlePage(page);
}

/**
 * Go to a collection, make it public, and give user1 owner access to it, via
 * the access control dialog.
 */
async function makeCollectionPublic(page: Page, collection: string) {
    await gotoCollection(page, collection);
    await page.locator('.g-collection-actions-button:visible').click();
    await page.locator('.g-collection-access-control:visible').click();
    await waitForDialog(page);
    await page.locator('#g-access-public').click();
    await expect(page.locator('.radio.g-selected')).toContainText('Public');

    // Search for user1 and add it to the access list.
    await page.locator('#g-dialog-container .g-search-field').fill('user1');
    const userResult = page.locator('.g-search-result-element[data-resource-type="user"]');
    await expect(userResult).toHaveCount(1);
    await userResult.click();
    await expect(page.locator('.g-user-access-entry')).toHaveCount(2);

    // Give user1 owner (ADMIN) access, matching the original spec's value of 2.
    await page.locator('.g-user-access-entry').nth(1).locator('select').selectOption('2');
    await page.locator('.g-save-access-list').click();
    await expect(page.locator('#g-dialog-container')).toBeHidden();
    await waitForIdlePage(page);
}

/** Open the policies dialog from a collection's actions menu. */
async function openCollectionPolicies(page: Page) {
    await page.locator('.g-collection-actions-button:visible').click();
    await expect(page.locator('.g-collection-policies:visible')).toHaveCount(1);
    await page.locator('.g-collection-policies:visible').click();
}

/** Open the policies dialog from a user's actions menu. */
async function openUserPolicies(page: Page) {
    await page.locator('.g-user-actions-button:visible').click();
    await expect(page.locator('.g-user-policies:visible')).toHaveCount(1);
    await page.locator('.g-user-policies:visible').click();
}

/**
 * Test the quota dialog as an admin: the quota can be edited, an invalid
 * value is rejected, and the chart is shown when a quota is in effect.
 */
async function testQuotaDialogAsAdmin(page: Page, hasChart: boolean, capacity: string) {
    await waitForDialog(page);
    await expect(page.locator('.g-quota-capacity')).toHaveCount(1);
    await expect(page.locator('a.btn-default')).toHaveCount(1);
    await expect(page.locator(hasChart ? '.g-has-chart' : '.g-no-chart')).toHaveCount(1);
    await expect(page.locator('#g-user-quota-size-value')).toHaveCount(1);

    // An invalid value must be rejected.  Filling the field also selects the
    // custom quota radio button.
    await page.locator('#g-user-quota-size-value').fill('abc');
    await page.locator('.g-save-policies').click();
    await expect(page.locator('.g-validation-failed-message')).toContainText('Invalid quota');

    await page.locator('#g-user-quota-size-value').fill(capacity);
    await page.locator('.g-save-policies').click();
    await expect(page.locator('#g-dialog-container')).toBeHidden();
    await waitForIdlePage(page);
}

/**
 * Test the quota dialog as a non-admin: the quota is displayed but cannot be
 * edited.
 */
async function testQuotaDialogAsUser(page: Page, hasChart: boolean) {
    await waitForDialog(page);
    await expect(page.locator('.g-quota-capacity')).toHaveCount(1);
    await expect(page.locator('a.btn-default')).toHaveCount(1);
    await expect(page.locator(hasChart ? '.g-has-chart' : '.g-no-chart')).toHaveCount(1);
    await expect(page.locator('#g-user-quota-size-value')).toHaveCount(0);

    await page.locator('a.btn-default').click();
    await expect(page.locator('#g-dialog-container')).toBeHidden();
    await waitForIdlePage(page);
}

/** Upload an in-memory file of the given size from the current folder view. */
async function uploadBuffer(page: Page, name: string, size: number, awaitSuccess = true) {
    await page.locator('.g-upload-here-button').first().click();
    await expect(page.locator('.g-drop-zone')).toBeVisible();
    await page.locator('#g-files').setInputFiles({
        name,
        mimeType: 'text/plain',
        buffer: Buffer.alloc(size, 'a'),
    });
    await page.locator('.g-start-upload').click();
    if (awaitSuccess) {
        await waitForIdlePage(page);
        await expect(page.locator('.g-start-upload')).toBeHidden();
    }
}

test.describe('Test the user quota plugin (full port from 3.x)', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('create resources', async ({ page }) => {
        await createUser(
            page, ADMIN.login, ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password,
        );
        await createCollection(page, 'Collection A');
        await createCollection(page, 'Collection B');

        await logout(page);
        await createUser(
            page, USER1.login, USER1.email, USER1.firstName, USER1.lastName, USER1.password,
        );
        await logout(page);
        await createUser(
            page, USER2.login, USER2.email, USER2.firstName, USER2.lastName, USER2.password,
        );
        await logout(page);
        await createUser(
            page, USER3.login, USER3.email, USER3.firstName, USER3.lastName, USER3.password,
        );
    });

    test('make the collections public', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await makeCollectionPublic(page, 'Collection A');
        await makeCollectionPublic(page, 'Collection B');
    });

    test('check that admin can set the default user quota', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        await page.locator('a.g-nav-link[g-target="admin"]').click();
        await expect(page.locator('.g-plugins-config')).toBeVisible();
        await page.locator('.g-plugins-config').click();
        await expect(page.locator('.g-plugin-list-item[data-name="user_quota"]')).toBeVisible();

        const configLink = page.locator(
            '.g-plugin-list-item[data-name="user_quota"] a.g-plugin-config-link[g-route="plugins/user_quota/config"]',
        );
        await expect(configLink).toHaveCount(1);
        await configLink.click();
        await expect(page.locator('#g-user-quota-user-size-value')).toBeVisible();
        await waitForIdlePage(page);

        // An invalid value must be rejected.
        await page.locator('#g-user-quota-user-size-value').fill('abc');
        await page.locator('#g-user-quota-form input.btn-primary').click();
        await expect(page.locator('#g-user-quota-error-message')).toContainText('Invalid quota');

        await page.locator('#g-user-quota-user-size-value').fill('512000');
        await page.locator('#g-user-quota-form input.btn-primary').click();
        await expect.poll(() => getSetting(page, 'user_quota.default_user_quota')).toBe(512000);
        await waitForIdlePage(page);
    });

    test('check that admin can set quota for collections and users', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        // Collection A starts with no explicit quota and no default, so no chart.
        await gotoCollection(page, 'Collection A');
        await openCollectionPolicies(page);
        await waitForDialog(page);
        routes.collectionDialogRoute = await page.evaluate(() => window.location.hash);
        await testQuotaDialogAsAdmin(page, false, '2048');

        // Now that a quota is in effect a chart is shown.
        await openCollectionPolicies(page);
        await testQuotaDialogAsAdmin(page, true, '32 kB');

        // Set a quota on user1.
        await gotoUser(page, 'Quota User');
        routes.userRoute = await page.evaluate(() => window.location.hash);
        await openUserPolicies(page);
        await waitForDialog(page);
        routes.userDialogRoute = await page.evaluate(() => window.location.hash);
        await testQuotaDialogAsAdmin(page, true, '2048');
    });

    test('test routes', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        expect(routes.collectionDialogRoute).toContain('dialog=quota');
        expect(routes.userDialogRoute).toContain('dialog=quota');

        await navigate(page, routes.collectionDialogRoute);
        await waitForDialog(page);
        await expect(page.locator('.g-quota-capacity')).toHaveCount(1);

        await navigate(page, routes.userRoute);
        await waitForIdlePage(page);
        await expect(page.locator('.g-user-name')).toHaveText('Quota User');

        await navigate(page, routes.userDialogRoute);
        await waitForDialog(page);
        await expect(page.locator('.g-quota-capacity')).toHaveCount(1);

        await page.locator('#g-dialog-container a[data-dismiss="modal"]').click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();
        await waitForIdlePage(page);
    });

    test('upload honors the quota of the owning user', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        // user1 has a 2048 byte quota and a public folder.  Uploading 2048
        // bytes fills it exactly; uploading another 2048 bytes must fail.
        await gotoUser(page, 'Quota User');
        await expect(page.locator('a.g-folder-list-link').first()).toBeVisible();
        await page.locator('a.g-folder-list-link').first().click();
        await expect(page.locator('.g-upload-here-button:visible')).toBeVisible();
        await waitForIdlePage(page);

        await uploadBuffer(page, 'quota_fill.txt', 2048);
        await uploadBuffer(page, 'quota_overflow.txt', 2048, false);
        await expect(page.getByText('file storage quota')).toBeVisible();
    });

    test('check that user1 can view but not set quota', async ({ page }) => {
        await login(page, USER1.login, USER1.password);

        await gotoCollection(page, 'Collection A');
        await openCollectionPolicies(page);
        await testQuotaDialogAsUser(page, true);

        await gotoUser(page, 'Quota User');
        await openUserPolicies(page);
        await testQuotaDialogAsUser(page, true);
    });

    test('check that a different user does not see quota', async ({ page }) => {
        await login(page, USER2.login, USER2.password);

        await gotoCollection(page, 'Collection A');
        await page.locator('.g-collection-actions-button:visible').click();
        await expect(page.locator('.g-download-collection:visible')).toHaveCount(1);
        await expect(page.locator('.g-collection-policies')).toHaveCount(0);

        await gotoUser(page, 'Quota User');
        await expect(page.locator('.g-user-actions-button')).toHaveCount(0);
    });

    test('check that admin can set the default collection quota', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        await page.locator('a.g-nav-link[g-target="admin"]').click();
        await expect(page.locator('.g-plugins-config')).toBeVisible();
        await page.locator('.g-plugins-config').click();
        await expect(page.locator('.g-plugin-list-item[data-name="user_quota"]')).toBeVisible();

        const configLink = page.locator(
            '.g-plugin-list-item[data-name="user_quota"] a.g-plugin-config-link[g-route="plugins/user_quota/config"]',
        );
        await configLink.click();
        await expect(page.locator('#g-user-quota-collection-size-value')).toBeVisible();
        await waitForIdlePage(page);

        await page.locator('#g-user-quota-collection-size-value').fill('256000');
        await page.locator('#g-user-quota-form input.btn-primary').click();
        await expect.poll(() => getSetting(page, 'user_quota.default_collection_quota')).toBe(256000);
        await waitForIdlePage(page);
    });

    test('check that a user that has never had their quota altered sees the default', async ({ page }) => {
        await login(page, USER3.login, USER3.password);

        await gotoUser(page, 'Third User');
        await openUserPolicies(page);
        await testQuotaDialogAsUser(page, true);
    });

    test('check that a collection that has never had their quota altered sees the default', async ({ page }) => {
        await login(page, USER1.login, USER1.password);

        await gotoCollection(page, 'Collection B');
        await openCollectionPolicies(page);
        await testQuotaDialogAsUser(page, true);
    });
});
