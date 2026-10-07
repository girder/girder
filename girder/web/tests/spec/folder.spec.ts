import path from 'path';
import { fileURLToPath } from 'url';

import { Page, expect, test } from '@playwright/test';

import { createUser, login, logout, waitForDialog, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/folderSpec.js
 *
 * Tests folder creation, editing, deletion, the folder metadata widget, folder
 * access control, and folder navigation.  The original spec used a single
 * sequential Jasmine describe; this port keeps the same sequence using a
 * serial Playwright describe.  Each test gets a fresh page, so tests that need
 * a logged-in session log in again and navigate back to the resource they
 * need.  The server and its database are shared across the whole describe.
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

const FOLDER_NAME = 'Test Folder Name';

// Set when the subfolder is created, then reused by the later tests.
let folderId = '';

/** Navigate within the single page app (equivalent of girderTest.testRoute). */
async function navigate(page: Page, route: string) {
    await page.evaluate((r) => {
        // @ts-ignore - window.girder is available at runtime
        window.girder.router.navigate(r, { trigger: true });
    }, route);
}

async function waitForUsersPage(page: Page) {
    await expect(page.locator('a.g-nav-link[g-target="users"]:visible')).toBeVisible();
    await page.locator('a.g-nav-link[g-target="users"]').click();
    await expect(page.locator('.g-user-search-form .g-search-field:visible')).toBeEnabled();
    await waitForIdlePage(page);
}

/** Log in, go to the users page, and open the admin user's page. */
async function openAdminUserPage(page: Page) {
    await login(page, ADMIN.login, ADMIN.password);
    await waitForUsersPage(page);
    await expect(page.locator('.g-user-list-entry')).toHaveCount(1);
    await page.locator('a.g-user-link', { hasText: 'Admin' }).click();
    await expect(page.locator('.g-user-name')).toHaveText('Admin Admin');
    await expect(page.locator('.g-user-actions-button')).toHaveCount(1);
    await waitForIdlePage(page);
}

/** Navigate directly (full page load) to a folder route. */
async function gotoFolder(page: Page, id: string) {
    const base = page.url().split('#')[0];
    await page.goto(`${base}#folder/${id}`);
    await page.reload();
    await expect(page.locator('.g-folder-actions-button:visible')).toBeVisible();
    await waitForIdlePage(page);
}

/** Show the folder edit dialog and click a button. */
async function editFolder(page: Page, button: 'cancel' | 'save', testValidation = false) {
    await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
    await page.locator('.g-folder-actions-button:visible').click();
    await expect(page.locator('.g-edit-folder:visible')).toHaveCount(1);
    await page.locator('.g-edit-folder:visible').click();
    await waitForDialog(page);
    await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=folderedit');

    const actionButton = button === 'cancel'
        ? page.locator('#g-dialog-container .btn-default')
        : page.locator('#g-dialog-container button.g-save-folder');
    await expect(page.locator('#g-name')).not.toHaveValue('');
    await expect(actionButton).toHaveText(button === 'cancel' ? 'Cancel' : 'Save');

    if (testValidation) {
        await expect(page.locator('.g-upload-footer')).toHaveCount(1);

        // Empty names are rejected.
        const oldval = await page.locator('#g-name').inputValue();
        await page.locator('#g-name').fill('');
        await page.locator('#g-dialog-container .g-save-folder').click();
        await expect(page.locator('.g-validation-failed-message')).toHaveText('Folder name must not be empty.');

        // A disallowed extension is rejected.
        await page.locator('#g-name').fill(oldval);
        await page.locator('.g-markdown-drop-zone .g-file-input').setInputFiles(path.join(dataDir, 'testFile.txt'));
        await expect(
            page.locator('#g-alerts-container .alert-danger').filter({
                hasText: 'Only files with the following extensions are allowed: png, jpg, jpeg, gif.',
            }),
        ).toBeVisible();

        // An allowed extension is uploaded and attached to the markdown.
        await page.locator('.g-markdown-drop-zone .g-file-input').setInputFiles(path.join(dataDir, 'fake.jpg'));
        await expect(page.locator('#g-dialog-container .g-markdown-text')).toHaveValue(
            /!\[fake\.jpg]\(.*\/download\)/,
        );

        // The preview shows the uploaded image.
        await page.locator('#g-dialog-container .g-preview-link').click();
        await expect(page.locator('.g-markdown-preview img')).toHaveCount(1);

        // Back to the write tab, then test a too-large drag and drop.
        await page.locator('#g-dialog-container .g-write-link').click();
        await expect(page.locator('.g-markdown-text:visible')).toBeVisible();

        await testUploadDropAction(page, '.g-markdown-drop-zone', '.g-markdown-text.dragover', [
            { name: 'upload0.tmp', size: 10 * 1024 * 1024 + 1 },
        ]);
        await expect(
            page.locator('#g-alerts-container .alert-danger').filter({ hasText: 'That file is too large.' }),
        ).toBeVisible();
    }

    await actionButton.click();
    await waitForIdlePage(page);
}

/** Dispatch a native drag event (dragenter/dragleave/dragover) with no files. */
async function dispatchDrag(page: Page, selector: string, type: string) {
    await page.evaluate((args: { selector: string, type: string }) => {
        const el = document.querySelector(args.selector);
        el?.dispatchEvent(new DragEvent(args.type, {
            bubbles: true,
            cancelable: true,
            dataTransfer: new DataTransfer(),
        }));
    }, { selector, type });
}

/** Dispatch a native drop event carrying fake files of the given sizes. */
async function dispatchDrop(page: Page, selector: string, files: { name: string, size: number }[]) {
    await page.evaluate((args: { selector: string, files: { name: string, size: number }[] }) => {
        const dt = new DataTransfer();
        args.files.forEach((f) => {
            dt.items.add(new File([new Uint8Array(f.size)], f.name));
        });
        const el = document.querySelector(args.selector);
        const ev = new Event('drop', { bubbles: true, cancelable: true });
        Object.defineProperty(ev, 'dataTransfer', { value: { files: dt.files } });
        el?.dispatchEvent(ev);
    }, { selector, files });
}

/**
 * Port of girderTest.testUploadDropAction: exercise the drag and drop
 * enter/leave/drop cycle on the given drop zone.
 */
async function testUploadDropAction(
    page: Page,
    selector: string,
    dropActiveSelector: string,
    files: { name: string, size: number }[],
) {
    await dispatchDrag(page, selector, 'dragenter');
    await expect(page.locator(dropActiveSelector)).toHaveCount(1);

    await dispatchDrag(page, selector, 'dragleave');
    await expect(page.locator(dropActiveSelector)).toHaveCount(0);

    await dispatchDrag(page, selector, 'dragenter');
    await expect(page.locator(dropActiveSelector)).toHaveCount(1);

    // Dropping nothing clears the active state.
    await dispatchDrag(page, selector, 'dragover');
    await dispatchDrop(page, selector, []);
    await expect(page.locator(dropActiveSelector)).toHaveCount(0);

    await dispatchDrag(page, selector, 'dragenter');
    await expect(page.locator(dropActiveSelector)).toHaveCount(1);

    await dispatchDrop(page, selector, files);
}

/** Test the folder access control dialog: verify current, switch, and save. */
async function folderAccessControl(page: Page, current: 'public' | 'private', action: 'public' | 'private', recurse = false) {
    await expect(page.locator('.g-folder-access-button:visible')).toHaveCount(1);
    await page.locator('.g-folder-access-button').click();
    await waitForDialog(page);

    await expect(page.locator('#g-access-private:visible')).toBeEnabled();
    await expect(page.locator(`#g-access-${current}`)).toBeChecked();

    await page.locator(`#g-access-${action}`).click();
    if (recurse) {
        await page.locator('#g-apply-recursive').click();
    } else {
        await page.locator('#g-apply-nonrecursive').click();
    }

    await expect(page.locator('.radio.g-selected')).toContainText(action === 'private' ? 'Private' : 'Public');
    await expect(page.locator('.g-save-access-list:visible')).toBeEnabled();
    await page.locator('.g-save-access-list').click();
    await waitForIdlePage(page);
    await expect(page.locator('#g-dialog-container')).toBeHidden();
}

/* ------------------------------------------------------------------ *
 * Metadata widget helpers (port of girderTest.testMetadata).
 * ------------------------------------------------------------------ */

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

/* ------------------------------------------------------------------ *
 * Tests
 * ------------------------------------------------------------------ */

test.describe('Test folder creation, editing, and deletion', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('register a user', async ({ page }) => {
        await createUser(page, ADMIN.login, ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);
    });

    test('go to users page', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await waitForUsersPage(page);
    });

    test('view the users on the user page and click on one', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await waitForUsersPage(page);

        await expect(page.locator('.g-user-list-entry')).toHaveCount(1);
        await page.locator('a.g-user-link', { hasText: 'Admin' }).click();
        await expect(page.locator('.g-user-name')).toHaveText('Admin Admin');
        await expect(page.locator('.g-user-actions-button')).toHaveCount(1);
    });

    test('anonymous loading the private folder of the user prompts a login dialog', async ({ page }) => {
        await openAdminUserPage(page);

        await expect(page.locator('a.g-folder-list-link', { hasText: 'Private' })).toBeVisible();
        await page.locator('a.g-folder-list-link', { hasText: 'Private' }).click();
        await expect(page.locator('ol.breadcrumb>li.active')).toHaveText('Private');
        await waitForIdlePage(page);

        const privateFolderFragment = await page.evaluate(() => window.location.hash.slice(1));

        await logout(page);
        await navigate(page, privateFolderFragment);
        await waitForDialog(page);
        await expect(page.locator('input#g-login')).toBeVisible();
        await page.locator('.modal-header .close').click();
        await waitForIdlePage(page);

        await navigate(page, '');
        await login(page, ADMIN.login, ADMIN.password);

        // Get back to the user page so testing may continue.
        await waitForUsersPage(page);
        await expect(page.locator('.g-user-list-entry')).toHaveCount(1);
        await page.locator('a.g-user-link', { hasText: 'Admin' }).click();
        await expect(page.locator('.g-user-name')).toHaveText('Admin Admin');
        await expect(page.locator('.g-user-actions-button')).toHaveCount(1);
    });

    test('create a subfolder in the public folder of the user', async ({ page }) => {
        await openAdminUserPage(page);

        await expect(page.locator('a.g-folder-list-link', { hasText: 'Public' })).toBeVisible();
        await page.locator('a.g-folder-list-link', { hasText: 'Public' }).click();
        await expect(page.locator('.g-empty-parent-message:visible')).toBeVisible();
        await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);

        await page.locator('.g-folder-actions-button:visible').click();
        await expect(page.locator('a.g-create-subfolder:visible')).toHaveCount(1);
        await page.locator('.g-create-subfolder:visible').click();

        await waitForDialog(page);
        await expect.poll(() => page.evaluate(() => window.location.hash)).toContain('dialog=foldercreate');
        await expect(page.locator('#g-dialog-container a.btn-default:visible')).toHaveText('Cancel');

        // Creating a folder has no upload footer, but the name is required.
        await expect(page.locator('.g-upload-footer')).toHaveCount(0);
        await page.locator('#g-dialog-container .g-save-folder').click();
        await expect(page.locator('.g-validation-failed-message')).toHaveText('Folder name must not be empty.');

        await page.locator('#g-name').fill(FOLDER_NAME);
        await page.locator('.g-description-editor-container .g-markdown-text').fill('## Test Description');
        await page.locator('.g-description-editor-container .g-preview-link').click();
        await expect(page.locator('.g-markdown-preview h2', { hasText: 'Test Description' })).toHaveCount(1);

        await page.locator('#g-dialog-container .g-save-folder').click();
        await waitForIdlePage(page);

        const folderLink = page.locator('a.g-folder-list-link', { hasText: FOLDER_NAME });
        await expect(folderLink).toHaveCount(1);
        const href = await folderLink.getAttribute('href');
        folderId = (href || '').split('/').pop() as string;
        expect(folderId).not.toBe('');

        // The folder info dialog reports the empty contents.
        await page.locator('.g-folder-info-button').click();
        await waitForDialog(page);
        await expect(page.locator('.g-folder-info-line[property="nItems"]')).toHaveText('Contains 0 items totaling 0 B');
        await expect(page.locator('.g-folder-info-line[property="nFolders"]')).toHaveText('Contains 1 subfolders');
        await expect(page.locator('.g-folder-info-line[property="created"]')).toContainText('Created ');
        await expect(page.locator('.g-folder-description')).toHaveCount(0);
        await page.locator('.modal-footer a[data-dismiss="modal"]').click();
        await waitForIdlePage(page);

        // Navigate into the new folder.
        await page.locator('a.g-folder-list-link', { hasText: FOLDER_NAME }).click();
        await expect(page.locator('.breadcrumb .active', { hasText: FOLDER_NAME })).toHaveCount(1);
        await expect(page.locator('.breadcrumb .active')).toHaveText(FOLDER_NAME);
    });

    test('Open edit dialog and check url state', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoFolder(page, folderId);
        await editFolder(page, 'cancel');
    });

    test('Add, edit, and delete metadata for the folder', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoFolder(page, folderId);
        await testMetadata(page);
    });

    test('Open edit dialog and save the folder', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoFolder(page, folderId);
        await editFolder(page, 'save', true);
    });

    test('Test folder view and navigation', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoFolder(page, folderId);

        // Create an item in the folder.
        await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
        await page.locator('.g-folder-actions-button:visible').click();
        await expect(page.locator('a.g-create-item:visible')).toHaveCount(1);
        await page.locator('.g-create-item:visible').click();
        await waitForDialog(page);
        await expect(page.locator('#g-dialog-container a.btn-default:visible')).toHaveText('Cancel');
        await page.locator('#g-name').fill('Test Item Name');
        await page.locator('.g-save-item').click();

        const itemLink = page.locator('a.g-item-list-link', { hasText: 'Test Item Name' });
        await expect(itemLink).toHaveCount(1);
        await waitForIdlePage(page);

        // Open the item, then go back to the folder via the breadcrumb.
        await itemLink.click();
        await expect(page.locator('.g-item-name')).toContainText('Test Item Name');
        await expect(page.locator('a.g-item-breadcrumb-link').last()).toBeVisible();
        await waitForIdlePage(page);

        await page.locator('a.g-item-breadcrumb-link').last().click();
        await expect(page.locator('a.g-breadcrumb-link')).toHaveCount(2);
        await waitForIdlePage(page);

        // This folder shows metadata (added in the earlier test).
        expect(await page.locator('.g-widget-metadata-row').count()).not.toBe(0);
        await page.locator('i.icon-level-up').click();
        await expect(page.locator('a.g-breadcrumb-link')).toHaveCount(1);
        await waitForIdlePage(page);

        // The parent folder shows no metadata.
        expect(await page.locator('.g-widget-metadata-row').count()).toBe(0);
        await page.locator('a.g-breadcrumb-link').click();
        await expect(page.locator('a.g-breadcrumb-link')).toHaveCount(0);
        await waitForIdlePage(page);

        // The user page lists the two default folders again.
        await expect(page.locator('a.g-folder-list-link', { hasText: 'Public' })).toBeVisible();
        await page.locator('a.g-folder-list-link', { hasText: 'Public' }).click();
        const subfolderLink = page.locator('a.g-folder-list-link', { hasText: FOLDER_NAME });
        await expect(subfolderLink).toBeVisible();
        await subfolderLink.click();
        await expect(page.locator('a.g-breadcrumb-link')).toHaveCount(2);
        await waitForIdlePage(page);
    });

    test('Test folder access control', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await gotoFolder(page, folderId);
        await folderAccessControl(page, 'public', 'private');
    });

    test('Delete the folder', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        // Deleting a folder through the actions menu is handled asynchronously
        // by a local Celery worker.  The web test environment does not run a
        // worker, so that endpoint responds with 503.  Use the checked-resource
        // delete from the parent folder instead, which deletes synchronously.
        const parentId = await page.evaluate(async (fid: string) => {
            return await new Promise<string>((resolve, reject) => {
                // @ts-ignore - window.girder is available at runtime
                window.girder.rest.restRequest({ url: `/folder/${fid}`, method: 'GET' })
                    .done((folder: { parentId: string }) => resolve(folder.parentId))
                    .fail(reject);
            });
        }, folderId);
        await gotoFolder(page, parentId);

        // The parent (Public) contains only the folder to be deleted.
        await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
        await page.locator('.g-select-all').check();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-delete-checked')).toBeVisible();
        await page.locator('a.g-delete-checked').click();
        await expect(page.locator('#g-confirm-button:visible')).toBeVisible();
        await page.locator('#g-confirm-button').click();

        // The parent is now empty.
        await expect(page.locator('.g-empty-parent-message:visible')).toBeVisible();
        await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
        await waitForIdlePage(page);
        await expect(page.locator('.breadcrumb .active')).toHaveText('Public');
    });
});
