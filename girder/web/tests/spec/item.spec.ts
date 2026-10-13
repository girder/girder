import path from 'path';
import { fileURLToPath } from 'url';

import { Page, expect, test } from '@playwright/test';

import { createUser, login, waitForDialog, waitForFocused, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/itemSpec.js
 *
 * Tests item creation, editing, metadata, file management, and deletion.
 * The original spec used a single sequential Jasmine describe; this port
 * keeps the same sequence using a serial Playwright describe.  Each test
 * gets a fresh page, so tests that need a logged-in session log in again
 * and navigate back to the item they need.  The server and its database
 * are shared across the whole describe.
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.join(__dirname, 'data');

const ADMIN = {
    login: 'admin',
    email: 'admin@girder.test',
    firstName: 'Admin',
    lastName: 'Admin',
    password: 'adminpassword!',
};

const SECONDUSER = {
    login: 'seconduser',
    email: 'seconduser@girder.test',
    firstName: 'Second',
    lastName: 'User',
    password: 'password!',
};

const NONADMIN = {
    login: 'nonadmin',
    email: 'nonadmin@girder.test',
    firstName: 'Not',
    lastName: 'Admin',
    password: 'password!',
};

const ITEM_NAME = 'Test Item Name';
const ITEM_DESCRIPTION = 'Test Item Description';

// Set when the private item is created, then reused by the later tests.
let itemId = '';

/** Make a REST request from within the page context and await its result. */
async function asyncRestRequest(page: Page, opts: Record<string, unknown>) {
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

/** Navigate to the users list page. */
async function waitForUsersPage(page: Page) {
    await expect(page.locator('a.g-nav-link[g-target="users"]:visible')).toBeVisible();
    await page.locator('a.g-nav-link[g-target="users"]').click();
    await expect(page.locator('.g-user-search-form .g-search-field:visible')).toBeEnabled();
    await waitForIdlePage(page);
}

/** Log in, go to the users page, and open the "Not Admin" user's page. */
async function openNonAdminUserPage(page: Page) {
    await login(page, NONADMIN.login, NONADMIN.password);
    await waitForUsersPage(page);
    await expect(page.locator('a.g-user-link', { hasText: 'Not Admin' })).toBeVisible();
    await page.locator('a.g-user-link', { hasText: 'Not Admin' }).click();
    await expect(page.locator('.g-user-name')).toHaveText('Not Admin');
    await waitForIdlePage(page);
}

/** Navigate directly (full page load) to an item route. */
async function gotoItem(page: Page, id: string) {
    const base = page.url().split('#')[0];
    await page.goto(`${base}#item/${id}`);
    await page.reload();
    await expect(page.locator('.g-item-actions-button:visible')).toBeVisible();
    await waitForIdlePage(page);
}

/**
 * Create an item in the named Public or Private folder of the user whose
 * page is currently displayed, then open the item and check its contents.
 */
async function addItemToFolder(page: Page, folder: 'Public' | 'Private') {
    const isPublic = folder === 'Public';

    await expect(page.locator('a.g-folder-list-link', { hasText: folder })).toBeVisible();
    await page.locator('a.g-folder-list-link', { hasText: folder }).click();

    await expect(page.locator('.g-empty-parent-message:visible')).toBeVisible();
    await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
    await page.locator('.g-folder-actions-button:visible').click();

    await expect(page.locator('a.g-create-item:visible')).toHaveCount(1);
    await page.locator('a.g-create-item:visible').click();

    await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=itemcreate');
    await waitForDialog(page);
    await expect(page.locator('#g-dialog-container a.btn-default:visible')).toHaveText('Cancel');

    await page.locator('#g-name').fill(ITEM_NAME);
    await page.locator('#item-description-write .g-markdown-text').fill(ITEM_DESCRIPTION);
    await page.locator('.g-save-item').click();

    await expect(page.locator('a.g-item-list-link', { hasText: ITEM_NAME })).toHaveCount(1);
    await waitForIdlePage(page);

    await expect(page.locator('li.g-item-list-entry')).toHaveAttribute('public', isPublic ? 'true' : 'false');
    await page.locator('a.g-item-list-link', { hasText: ITEM_NAME }).click();

    await expect(page.locator('.g-item-name', { hasText: ITEM_NAME })).toHaveCount(1);
    await expect(page.locator('.g-item-name')).toHaveText(ITEM_NAME);
    await expect(page.locator('.g-item-description')).toHaveText(ITEM_DESCRIPTION);
    await expect(page.locator('.g-item-id')).toContainText(/[a-f0-9]{24}/);
    await waitForIdlePage(page);
}

/** Show the item edit dialog and click a button. */
async function editItem(page: Page, action: 'cancel' | 'save') {
    await expect(page.locator('.g-item-actions-button:visible')).toHaveCount(1);
    await page.locator('.g-item-actions-button:visible').click();

    await expect(page.locator('.g-edit-item:visible')).toHaveCount(1);
    await page.locator('.g-edit-item:visible').click();

    await waitForDialog(page);
    await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('?dialog=itemedit');

    await expect(page.locator('#g-name')).not.toHaveValue('');

    const actionButton = action === 'cancel'
        ? page.locator('#g-dialog-container a.btn-default')
        : page.locator('#g-dialog-container button.g-save-item');
    await expect(actionButton).toHaveText(action === 'cancel' ? 'Cancel' : 'Save');

    await actionButton.click();
    await waitForIdlePage(page);
}


function escapeRegExp(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Locate a metadata row by its exact key text. */
function metadataRow(page: Page, key: string) {
    return page.locator('.g-widget-metadata-row').filter({
        has: page.locator('.g-widget-metadata-key').filter({ hasText: new RegExp(`^${escapeRegExp(key)}$`) }),
    });
}

/**
 * Locate the currently open metadata editor.  The `editing` class is not
 * removed when an edit finishes, so it cannot be used to find the active
 * editor; the presence of the key input identifies it instead.
 */
function editingRow(page: Page) {
    return page.locator('.g-widget-metadata-row').filter({
        has: page.locator('.g-widget-metadata-key-input'),
    });
}

async function clearAlerts(page: Page) {
    await page.evaluate(() => {
        document.querySelectorAll('#g-alerts-container .alert').forEach((el) => el.remove());
    });
}

/** Replace the value in an open JSON metadata editor using code mode. */
async function setJsonValue(page: Page, row: import('@playwright/test').Locator, value: unknown) {
    await row.locator('button.jsoneditor-modes').click();
    await row.locator('.jsoneditor-type-modes:visible').filter({ hasText: 'Code' }).click();

    const ace = row.locator('.ace_content');
    await expect(ace).toBeVisible();
    await ace.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(JSON.stringify(value));
    // Give the ace editor a moment to flush its change handler before saving.
    await page.waitForTimeout(200);
}

/**
 * Port of girderTest.testMetadata's _editMetadata.  Adds or edits a metadata
 * key, optionally expecting a validation error, then saves, cancels, or
 * deletes.  When origKey is null a new row is created.
 */
async function editMetadata(
    page: Page,
    origKey: string | null,
    key: string | null,
    value: string | unknown | null,
    action: 'save' | 'cancel' | 'delete' = 'save',
    errorMessage?: RegExp,
    type: 'simple' | 'json' = 'simple',
) {
    await clearAlerts(page);
    const before = await page.locator('.g-widget-metadata-row').count();
    let expectedNum = before;
    let row: import('@playwright/test').Locator;

    if (origKey === null) {
        await expect(page.locator('.g-widget-metadata-add-button:visible')).toHaveCount(1);
        await page.locator('.g-widget-metadata-add-button').click();
        await page.locator(`.g-add-${type}-metadata`).click();
        row = editingRow(page);
        await expect(row).toHaveCount(1);
    } else {
        row = metadataRow(page, origKey);
        await expect(row).toHaveCount(1);
        await row.locator('.g-widget-metadata-edit-button').click();
        row = editingRow(page);
        await expect(row).toHaveCount(1);
    }

    await expect(row.locator('.g-widget-metadata-key-input')).toHaveCount(1);
    if (type === 'simple') {
        await expect(row.locator('.g-widget-metadata-value-input')).toHaveCount(1);
    } else {
        await expect(row.locator('.g-json-editor')).toHaveCount(1);
    }

    if (key !== null) {
        await row.locator('.g-widget-metadata-key-input').fill(key);
    } else {
        key = await row.locator('.g-widget-metadata-key-input').inputValue();
    }

    if (type === 'simple') {
        if (value !== null) {
            await row.locator('.g-widget-metadata-value-input').fill(value as string);
        } else {
            value = await row.locator('.g-widget-metadata-value-input').inputValue();
        }
    } else if (value !== null) {
        await setJsonValue(page, row, value);
    }

    if (errorMessage) {
        await row.locator('.g-widget-metadata-save-button').click();
        await expect(
            page.locator('#g-alerts-container .alert').filter({ hasText: errorMessage }),
        ).toBeVisible();
        if (action === 'cancel') {
            await row.locator('.g-widget-metadata-cancel-button').click();
            await expect(page.locator('.g-widget-metadata-key-input')).toHaveCount(0);
        }
        return;
    }

    switch (action) {
        case 'cancel':
            await row.locator('.g-widget-metadata-cancel-button').click();
            break;
        case 'delete':
            await row.locator('.g-widget-metadata-delete-button').click();
            await waitForDialog(page);
            await expect(page.locator('#g-confirm-button:visible')).toBeVisible();
            await page.locator('#g-confirm-button').click();
            expectedNum -= 1;
            await waitForIdlePage(page);
            break;
        default:
            await row.locator('.g-widget-metadata-save-button').click();
            if (origKey === null) {
                expectedNum += 1;
            }
            break;
    }

    await expect(page.locator('.g-widget-metadata-key-input')).toHaveCount(0);
    await expect(page.locator('.g-widget-metadata-row')).toHaveCount(expectedNum);

    if (action === 'save') {
        const saved = metadataRow(page, key);
        await expect(saved).toHaveCount(1);
        const savedValue = await saved.getAttribute('g-value');
        if (type === 'json') {
            expect(savedValue).toBe(JSON.stringify(value, null, 4));
        } else {
            expect(savedValue).toBe(value);
        }
    }
}

/**
 * Port of girderTest.testMetadata's _toggleMetadata: convert a metadata row
 * between the simple and JSON editors and save or cancel.
 */
async function toggleMetadata(
    page: Page,
    key: string,
    beforeType: 'simple' | 'json',
    action: 'save' | 'cancel' = 'save',
    errorMessage?: RegExp,
) {
    await clearAlerts(page);
    let row = metadataRow(page, key);
    await expect(row).toHaveCount(1);
    const beforeValue = await row.getAttribute('g-value');

    await row.locator('.g-widget-metadata-edit-button').click();
    row = editingRow(page);
    await expect(row.locator('.g-widget-metadata-toggle-button')).toHaveCount(1);
    await row.locator('.g-widget-metadata-toggle-button').click();

    if (errorMessage) {
        await row.locator(`.g-widget-metadata-${action}-button`).click();
        await expect(
            page.locator('#g-alerts-container .alert').filter({ hasText: errorMessage }),
        ).toBeVisible();
        return;
    }

    await row.locator(`.g-widget-metadata-${action}-button`).click();
    await expect(page.locator('.g-widget-metadata-key-input')).toHaveCount(0);

    const afterValue = await metadataRow(page, key).getAttribute('g-value');
    if (action === 'cancel') {
        expect(afterValue).toBe(beforeValue);
    } else if (beforeType === 'json') {
        expect(afterValue).toBe(JSON.stringify(JSON.parse(beforeValue as string)));
    } else {
        expect(afterValue).toBe(JSON.stringify(JSON.parse(beforeValue as string), null, 4));
    }
}

async function testMetadata(page: Page) {
    await editMetadata(page, null, 'simple_key', 'simple_value');
    await editMetadata(page, null, 'simple_key', 'duplicate_key_should_fail', 'cancel', /.*simple_key is already a metadata key/);
    await editMetadata(page, null, '', 'no_key', 'cancel', /.*A key is required for all metadata/);
    await editMetadata(page, null, 'cancel_me', 'this will be cancelled', 'cancel');
    await editMetadata(page, null, 'long_key', 'long_value' + new Array(2048).join('-'));
    await editMetadata(page, null, 'json_key', JSON.stringify({ sample_json: 'value' }, null, 4));
    await editMetadata(page, null, 'unicode_key\u00A9\uD834\uDF06', 'unicode_value\u00A9\uD834\uDF06');
    await editMetadata(page, 'simple_key', null, 'new_value', 'cancel');
    await editMetadata(page, 'long_key', 'json_key', null, 'cancel', /.*json_key is already a metadata key/);
    await editMetadata(page, 'simple_key', null, 'new_value');
    await editMetadata(page, 'simple_key', null, null, 'delete');
    await editMetadata(page, 'json_key', 'json_rename', null);

    await editMetadata(page, null, 'plain_json', { some: 'json' }, 'save', undefined, 'json');
    await editMetadata(page, null, 'non_object_or_array_json', false, 'save', undefined, 'json');
    await toggleMetadata(page, 'non_object_or_array_json', 'json');

    // Converting JSON to simple.
    await editMetadata(page, null, 'a_json_key', { foo: 'bar' }, 'save', undefined, 'json');
    await editMetadata(page, 'a_json_key', 'a_json_key', { foo: 'bar' }, 'cancel', undefined, 'json');
    await toggleMetadata(page, 'a_json_key', 'json');

    // A simple key that happens to be valid JSON.
    await editMetadata(page, null, 'a_simple_key', '{"some": "json"}');
    await toggleMetadata(page, 'a_simple_key', 'simple');

    // Converting and canceling.
    await editMetadata(page, null, 'a_canceled_key', '{"with": "json"}');
    await toggleMetadata(page, 'a_canceled_key', 'simple', 'cancel');

    // A simple key that is not valid JSON.
    await editMetadata(page, null, 'some_simple_key', 'foobar12345');
    await toggleMetadata(page, 'some_simple_key', 'simple', 'save', /The simple field is not valid JSON and can not be converted./);
}


test.describe('Test item creation, editing, and deletion', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('register a user (first is admin)', async ({ page }) => {
        await createUser(page, ADMIN.login, ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);
    });

    test('register another user', async ({ page }) => {
        await createUser(page, SECONDUSER.login, SECONDUSER.email, SECONDUSER.firstName, SECONDUSER.lastName, SECONDUSER.password);
    });

    test('register a third user', async ({ page }) => {
        await createUser(page, NONADMIN.login, NONADMIN.email, NONADMIN.firstName, NONADMIN.lastName, NONADMIN.password);
    });

    test('view the users on the user page and click on one', async ({ page }) => {
        await openNonAdminUserPage(page);

        // Check for actions menu.
        await expect(page.locator('button.g-user-actions-button')).toHaveCount(1);
    });

    test('create an item in the public folder of the user', async ({ page }) => {
        await openNonAdminUserPage(page);
        await addItemToFolder(page, 'Public');
    });

    test('go to users page and view the users and click on one', async ({ page }) => {
        await openNonAdminUserPage(page);
    });

    test('create an item in the private folder of the user', async ({ page }) => {
        await openNonAdminUserPage(page);
        await addItemToFolder(page, 'Private');

        // Capture the id of the item for the tests that follow.
        const hash = await page.evaluate(() => window.location.hash);
        itemId = hash.split('/')[1].split('?')[0];
        expect(itemId).toMatch(/[a-f0-9]{24}/);
    });

    test('Open edit dialog and check url state', async ({ page }) => {
        await login(page, NONADMIN.login, NONADMIN.password);
        await gotoItem(page, itemId);
        await editItem(page, 'cancel');
    });

    test('Add, edit, and delete metadata for the item', async ({ page }) => {
        await login(page, NONADMIN.login, NONADMIN.password);
        await gotoItem(page, itemId);
        await testMetadata(page);
    });

    test('Open edit dialog and save the item', async ({ page }) => {
        await login(page, NONADMIN.login, NONADMIN.password);
        await gotoItem(page, itemId);
        await editItem(page, 'save');
    });

    test('Edit files', async ({ page }) => {
        await login(page, NONADMIN.login, NONADMIN.password);
        await gotoItem(page, itemId);

        // Create a link file.
        await asyncRestRequest(page, {
            url: 'file',
            method: 'POST',
            data: {
                parentType: 'item',
                parentId: itemId,
                name: 'File 1',
                linkUrl: 'http://nowhere.com/file1',
            },
        });
        await waitForIdlePage(page);

        // Upload a file into the item.
        await expect(page.locator('.g-upload-into-item:visible')).toHaveCount(1);
        await page.locator('.g-upload-into-item').click();
        await waitForDialog(page);
        await page.locator('#g-files').setInputFiles(path.join(dataDir, 'testFile.txt'));
        await expect(page.locator('.g-overall-progress-message i.icon-ok')).toHaveCount(1);
        await page.locator('.g-start-upload').click();
        await waitForIdlePage(page);
        await expect(page.locator('.g-file-list-entry')).toHaveCount(2);

        /* Reload the item page through the edit dialog, then try to edit
         * each file in turn.  They must have different ids. */
        await editItem(page, 'save');
        await expect(page.locator('.g-file-list-entry .g-update-info')).toHaveCount(2);

        await page.locator('.g-file-list-entry .g-update-info').first().click();
        await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=fileedit&');
        await waitForDialog(page);
        await expect(page.locator('#g-name')).not.toHaveValue('');
        await waitForFocused(page, '#g-name');
        await expect(page.locator('#g-dialog-container a.btn-default')).toHaveText('Cancel');

        // An empty file name is rejected.
        await page.locator('#g-name').fill('');
        await page.locator('button.g-save-file').click();
        await expect(page.locator('.modal-dialog .g-validation-failed-message')).toHaveText('File name must not be empty.');

        const fileId1 = (await page.evaluate(() => window.location.hash)).split('dialogid=')[1];
        await page.locator('#g-dialog-container a.btn-default').click();
        await waitForIdlePage(page);

        await expect(page.locator('.g-file-list-entry .g-update-info')).toHaveCount(2);
        await page.locator('.g-file-list-entry .g-update-info').nth(1).click();
        await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=fileedit&');
        await waitForDialog(page);
        await expect(page.locator('#g-name')).not.toHaveValue('');
        await expect(page.locator('button.g-save-file')).toContainText('Save');

        const fileId2 = (await page.evaluate(() => window.location.hash)).split('dialogid=')[1];
        expect(fileId2 === fileId1).toBe(false);
        await page.locator('button.g-save-file').click();
        await waitForIdlePage(page);

        // Delete the file.
        await expect(page.locator('.g-file-list-entry')).toHaveCount(2);
        await page.locator('.g-file-actions-container').first().locator('.g-delete-file').click();
        await expect(page.locator('.modal-body')).toContainText('Are you sure you want to delete the file');
        await expect(page.locator('#g-confirm-button:visible')).toBeVisible();
        await page.locator('#g-confirm-button').click();

        await expect(page.locator('.g-file-list-entry')).toHaveCount(1);
        await waitForIdlePage(page);
    });

    test('Delete the item', async ({ page }) => {
        await login(page, NONADMIN.login, NONADMIN.password);
        await gotoItem(page, itemId);

        await expect(page.locator('.g-item-actions-button:visible')).toHaveCount(1);
        await page.locator('.g-item-actions-button:visible').click();

        await expect(page.locator('.g-delete-item:visible')).toHaveCount(1);
        await page.locator('.g-delete-item:visible').click();

        await waitForDialog(page);
        await expect(page.locator('#g-confirm-button:visible')).toBeVisible();
        await page.locator('#g-confirm-button').click();

        // Go back to the item list.
        await expect(page.locator('.g-item-list-container')).toHaveCount(1);
        await waitForIdlePage(page);
        await expect(page.locator('li.g-item-list-entry', { hasText: ITEM_NAME })).toHaveCount(0);
    });
});
