import fs from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

import { Page, expect, test } from '@playwright/test';

import { createUser, logout, upload, waitForDialog, waitForIdlePage } from '../util';
import { setupServer } from '../server';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/dataSpec.js
 *
 * These tests exercise the data hierarchy: creating folders, uploading and
 * downloading files and folders, quick search, checked-resource actions, and
 * the FileModel static upload helpers.
 */

/** Make a REST request from the page context (in the browser). */
async function api(page: Page, opts: Record<string, unknown>) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.rest.restRequest(opts).done((resp: unknown) => resolve(resp)).fail((resp: unknown) => reject(resp));
        });
    }, opts);
}

/** Return the id of one of the current user's top level folders by name. */
async function getUserFolderId(page: Page, name: string): Promise<string> {
    const me = await page.evaluate(() => {
        // @ts-ignore - window.girder is available at runtime
        return window.girder.auth.getCurrentUser().get('_id');
    });
    const folders = await api(page, {
        url: '/folder',
        method: 'GET',
        data: { parentType: 'user', parentId: me },
    }) as { _id: string, name: string }[];
    const folder = folders.find((f) => f.name === name);
    if (!folder) {
        throw new Error(`Could not find user folder ${name}`);
    }
    return folder._id;
}

/** Create a folder via the REST API. */
async function createFolderApi(page: Page, parentType: string, parentId: string, name: string) {
    return await api(page, {
        url: '/folder',
        method: 'POST',
        data: { parentType, parentId, name },
    }) as { _id: string };
}

/** Navigate directly (full page load) to a folder route. */
async function gotoFolder(page: Page, folderId: string) {
    const base = page.url().split('#')[0];
    await page.goto(`${base}#folder/${folderId}`);
    // A hash-only change does not reload the page; force a full load so the
    // app re-reads server settings such as core.show_download.
    await page.reload();
}

/** Read a system setting, returning undefined if unset. */
async function getSetting(page: Page, key: string) {
    try {
        return await api(page, { url: 'system/setting', method: 'GET', data: { key } });
    } catch {
        return undefined;
    }
}

/** Set a system setting. */
async function setSetting(page: Page, key: string, value: unknown) {
    await api(page, { url: 'system/setting', method: 'PUT', data: { key, value } });
}

/** Write a temporary file of the given size and return its path. */
function makeTempFile(name: string, size: number, fill = 'x') {
    const file = path.join(os.tmpdir(), name);
    fs.writeFileSync(file, Buffer.alloc(size, fill));
    return file;
}

/**
 * Start an upload, force the first chunk request to fail, then either resume
 * it or abort it.  Uses the real upload widget and a real (possibly chunked)
 * file so the resume/abort UI is exercised.  When abort is true the upload is
 * expected to have no effect.
 */
async function uploadWithResume(page: Page, file: string, abort = false) {
    let failed = false;
    const handler = async (route: import('@playwright/test').Route) => {
        if (!failed) {
            failed = true;
            await route.fulfill({
                status: 500,
                contentType: 'application/json',
                body: JSON.stringify({ message: 'simulated failure' }),
            });
        } else {
            await route.continue();
        }
    };
    await page.route('**/file/chunk*', handler);
    await page.locator('.g-upload-here-button').first().click();
    await expect(page.locator('.g-drop-zone')).toBeVisible();
    await page.locator('#g-files').setInputFiles(file);
    await page.locator('.g-start-upload').click();
    await expect(page.locator('.g-resume-upload:visible')).toBeVisible();
    if (abort) {
        await page.locator('#g-dialog-container .modal-footer a.btn-default').click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();
    } else {
        await page.locator('.g-resume-upload').click();
        await expect(page.locator('.g-start-upload')).toBeHidden();
        await waitForIdlePage(page);
    }
    await page.unroute('**/file/chunk*', handler);
}

test.describe('Create a data hierarchy', () => {
    setupServer();

    test('create a folder hierarchy with description and access control', async ({ page }) => {
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');

        // Go to the current user's folder list.
        await page.locator('.g-user-dropdown-link').click();
        await page.locator('a.g-my-folders').click();

        // The user has two default folders: Private and Public.
        await expect(page.locator('li.g-folder-list-entry').first()).toBeVisible();
        await expect(page.locator('.g-subfolder-count')).toHaveText('2');
        await expect(page.locator('a.g-folder-list-link').first()).toHaveText('Private');
        await expect(page.locator('.g-folder-privacy').first()).toHaveText('Private');

        // Descend into the Private folder.
        await page.locator('a.g-folder-list-link').first().click();
        await expect(page.locator('ol.breadcrumb>li.active')).toHaveText('Private');
        await expect(page.locator('.g-empty-parent-message:visible')).toBeVisible();

        // Create a subfolder with a description.
        await page.locator('.g-folder-actions-button').click();
        await page.locator('.g-create-subfolder').click();
        await waitForDialog(page);
        await expect(page.locator('input#g-name')).toBeVisible();
        await page.locator('input#g-name').fill("John's subfolder");
        const descBox = page.locator('.g-description-editor-container .g-markdown-text');
        await expect(descBox).toBeVisible();
        await descBox.fill('Some description');
        await page.locator('.g-save-folder').click();
        await waitForIdlePage(page);

        await expect(page.locator('li.g-folder-list-entry').first()).toBeVisible();
        await expect(page.locator('a.g-folder-list-link').first()).toHaveText("John's subfolder");
        await expect(page.locator('.g-folder-privacy').first()).toHaveText('Private');

        // Recursively set this folder to public, and verify it.
        await page.locator('.g-folder-access-button').click();
        await waitForDialog(page);
        await expect(page.locator('#g-access-private')).toBeChecked();
        await page.locator('#g-access-public').click();
        await page.locator('#g-apply-recursive').click();
        await expect(page.locator('.radio.g-selected')).toContainText('Public');
        await page.locator('.g-save-access-list').click();
        await waitForIdlePage(page);
        await expect(page.locator('.g-folder-privacy').first()).toHaveText('Public');

        // Change it back to private recursively.
        await page.locator('.g-folder-access-button').click();
        await waitForDialog(page);
        await expect(page.locator('#g-access-public')).toBeChecked();
        await page.locator('#g-access-private').click();
        await page.locator('#g-apply-recursive').click();
        await expect(page.locator('.radio.g-selected')).toContainText('Private');
        await page.locator('.g-save-access-list').click();
        await waitForIdlePage(page);
        await expect(page.locator('.g-folder-privacy').first()).toHaveText('Private');

        // Descend into the subfolder and verify the description appears in the
        // breadcrumb bar, then edit the folder.
        await page.locator('a.g-folder-list-link').first().click();
        await expect(page.locator('.g-hierarchy-breadcrumb-bar')).toContainText('Some description');
        await page.locator('.g-folder-actions-button').click();
        await page.locator('a.g-edit-folder').click();
        await waitForDialog(page);
        await expect(page.locator('.g-description-editor-container .g-markdown-text')).toHaveValue('Some description');
        await expect(page.locator('.g-save-folder')).toBeVisible();
        await page.locator('button.g-save-folder').click();
        await waitForIdlePage(page);
    });

});

test.describe('Download visibility setting', () => {
    setupServer();

    test('upload, download, and hide downloads via the setting', async ({ page }) => {
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
        const privateId = await getUserFolderId(page, 'Private');
        await gotoFolder(page, privateId);
        await expect(page.locator('.g-upload-here-button:visible')).toBeVisible();

        await upload(page, path.join(__dirname, 'data', 'testFile.txt'));
        await expect(page.locator('.g-item-count')).toHaveText('1');
        await expect(page.locator('.g-subfolder-count')).toHaveText('0');

        // Download the file from the item page.
        await page.locator('.g-item-list-link').first().click();
        await expect(page.locator('a.g-file-list-link')).toBeVisible();
        const fileHref = await page.locator('a.g-file-list-link').first().getAttribute('href');
        expect(fileHref).toMatch(/\/api\/v1\/file\/.+\/download$/);
        const [fileDownload] = await Promise.all([
            page.waitForEvent('download'),
            page.locator('a.g-file-list-link').first().click(),
        ]);
        expect(fileDownload.url()).toMatch(/\/api\/v1\/file\/.+\/download$/);

        // With downloads hidden, the file is not a link and the item has no
        // download action.
        const originalShowDownload = await getSetting(page, 'core.show_download');
        await setSetting(page, 'core.show_download', 'none');
        await page.reload();
        await expect(page.locator('span.g-file-list-link')).toHaveCount(1);
        await expect(page.locator('a.g-file-list-link')).toHaveCount(0);
        await page.locator('.g-item-actions-button').click();
        await expect(page.locator('a.g-download-item')).toHaveCount(0);
        await setSetting(page, 'core.show_download', originalShowDownload ?? 'all');

        // Download the folder.
        await gotoFolder(page, privateId);
        await expect(page.locator('.g-folder-actions-button:visible')).toBeVisible();
        await page.locator('.g-folder-actions-button').click();
        const folderHref = await page.locator('a.g-download-folder').getAttribute('href');
        expect(folderHref).toMatch(/\/api\/v1\/folder\/.+\/download$/);
        const [folderDownload] = await Promise.all([
            page.waitForEvent('download'),
            page.locator('a.g-download-folder').click(),
        ]);
        expect(folderDownload.url()).toMatch(/\/api\/v1\/folder\/.+\/download$/);

        // With downloads hidden, the folder has no download action.
        await setSetting(page, 'core.show_download', 'none');
        await page.reload();
        await expect(page.locator('.g-folder-actions-button:visible')).toBeVisible();
        await page.locator('.g-folder-actions-button').click();
        await expect(page.locator('.g-download-folder')).toHaveCount(0);
        await setSetting(page, 'core.show_download', originalShowDownload ?? 'all');

        // Download checked resources.  Create a second resource so there are
        // two checkboxes.
        await createFolderApi(page, 'folder', privateId, 'subfolder');
        await gotoFolder(page, privateId);
        await expect(page.locator('.g-list-checkbox').nth(1)).toBeVisible();
        await page.locator('.g-list-checkbox').nth(0).click();
        await page.locator('.g-list-checkbox').nth(1).click();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-download-checked')).toBeVisible();
        const requestPromise = page.waitForRequest((request) =>
            request.method() === 'POST' && request.url().includes('/api/v1/resource/download'));
        await page.locator('a.g-download-checked').click();
        const request = await requestPromise;
        const postData = request.postData() ?? '';
        expect(postData).toContain('resources=');
        expect(decodeURIComponent(postData)).toMatch(/"folder"/);

        // With downloads hidden, there is no checked-download action.
        await setSetting(page, 'core.show_download', 'none');
        await page.reload();
        await expect(page.locator('.g-list-checkbox').nth(1)).toBeVisible();
        await page.locator('.g-list-checkbox').nth(0).click();
        await page.locator('.g-list-checkbox').nth(1).click();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-download-checked')).toHaveCount(0);
        await setSetting(page, 'core.show_download', originalShowDownload ?? 'all');
    });

});

test.describe('Quick search', () => {
    setupServer();

    test('search using the quick search box and by keyboard', async ({ page }) => {
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
        const me = await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            return window.girder.auth.getCurrentUser().get('_id');
        });
        const privateId = await getUserFolderId(page, 'Private');
        await createFolderApi(page, 'folder', privateId, "John's subfolder");
        await gotoFolder(page, privateId);
        await expect(page.locator('.g-upload-here-button:visible')).toBeVisible();
        await upload(page, path.join(__dirname, 'data', 'testFile.txt'));

        const field = page.locator('.g-quick-search-container input.g-search-field');
        const results = page.locator('.g-quick-search-container .g-search-results');

        // Searching for a term that produces no results closes the results menu.
        await field.fill('zzzz-no-match');
        await expect(results).not.toHaveClass(/open/);

        await field.fill('john');
        await expect(results).toHaveClass(/open/);
        // Two resources (folder and user) plus the "..." results-page entry.
        await expect(page.locator('.g-quick-search-container li.g-search-result')).toHaveCount(3);
        await expect(page.locator('.g-quick-search-container a[data-resource-type="folder"]')).toHaveCount(1);
        await expect(page.locator('.g-quick-search-container a[data-resource-type="user"]')).toHaveCount(1);

        // Clicking the user result navigates to the current user's page.
        await page.locator('.g-quick-search-container a[data-resource-type="user"]').click();
        await waitForIdlePage(page);
        expect(await page.evaluate(() => window.location.hash)).toBe(`#user/${me}`);

        // Keyboard control of the search results: navigate with arrow keys and
        // select with enter.
        await field.fill('john');
        await expect(results).toHaveClass(/open/);
        await field.press('ArrowUp');
        await field.press('ArrowUp');
        await field.press('ArrowUp');
        await field.press('ArrowDown');
        await expect(page.locator('.g-quick-search-container .g-search-selected')).toContainText('johndoe');
        await field.press('Enter');
        await waitForIdlePage(page);
        expect(await page.evaluate(() => window.location.hash)).toBe(`#user/${me}`);
    });

});

test.describe('Upload files of various sizes', () => {
    setupServer();

    test('upload files of various sizes, including resume and abort', async ({ page }) => {
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
        const privateId = await getUserFolderId(page, 'Private');
        await gotoFolder(page, privateId);
        await expect(page.locator('.g-upload-here-button:visible')).toBeVisible();

        const expectItemCount = async (count: number) => {
            await expect(page.locator('.g-item-count')).toHaveText(String(count));
        };

        // A file without an extension.
        await upload(page, path.join(__dirname, 'data', 'testFile2'));
        await expectItemCount(1);

        // A file specified by size.
        await upload(page, makeTempFile('data-small.bin', 11));
        await expectItemCount(2);

        // Use a small chunk size so the generated files require multiple chunks.
        await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.rest.setUploadChunkSize(1024);
        });
        await setSetting(page, 'core.upload_minimum_chunk_size', 1024);

        // An upload requiring a resume that succeeds.
        await uploadWithResume(page, makeTempFile('data-resume.bin', 1024 * 32));
        await expectItemCount(3);

        // An upload requiring a resume that is aborted.
        await uploadWithResume(page, makeTempFile('data-abort.bin', 1024 * 32), true);
        await expectItemCount(3);

        // A large file, using a larger chunk size to keep the test fast.
        await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.rest.setUploadChunkSize(1024 * 256);
        });
        await setSetting(page, 'core.upload_minimum_chunk_size', 1024 * 256);

        await upload(page, makeTempFile('data-large.bin', 1024 * 513));
        await expectItemCount(4);

        // A large file requiring a resume that succeeds.
        await uploadWithResume(page, makeTempFile('data-large-resume.bin', 1024 * 513));
        await expectItemCount(5);
    });
});

test.describe('Upload by dropping', () => {
    setupServer();

    test('upload files by dropping and reject directories', async ({ page }) => {
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
        const privateId = await getUserFolderId(page, 'Private');
        await gotoFolder(page, privateId);
        await expect(page.locator('.g-upload-here-button:visible')).toBeVisible();

        // The drag bullseye appears on dragenter and disappears on dragleave.
        await page.locator('.g-upload-here-button').click();
        await expect(page.locator('.g-drop-zone')).toBeVisible();
        await page.evaluate(() => {
            const el = document.querySelector('.g-drop-zone')!;
            el.dispatchEvent(new DragEvent('dragenter', { bubbles: true, cancelable: true, dataTransfer: new DataTransfer() }));
        });
        await expect(page.locator('.g-dropzone-show:visible')).toBeVisible();
        await page.evaluate(() => {
            const el = document.querySelector('.g-drop-zone')!;
            el.dispatchEvent(new DragEvent('dragleave', { bubbles: true, cancelable: true, dataTransfer: new DataTransfer() }));
        });
        await expect(page.locator('.g-dropzone-show:visible')).toHaveCount(0);

        // Drop a single file and upload it.
        await page.evaluate((names: string[]) => {
            const dt = new DataTransfer();
            names.forEach((name) => dt.items.add(new File([new Uint8Array(10).fill(97)], name, { type: 'text/plain' })));
            const items = names.map(() => ({ webkitGetAsEntry: () => ({ isFile: true }) }));
            const fake: unknown = { files: dt.files, items };
            const ev = new Event('drop', { bubbles: true, cancelable: true });
            Object.defineProperty(ev, 'dataTransfer', { value: fake });
            document.querySelector('.g-drop-zone')!.dispatchEvent(ev);
        }, ['upload0.tmp']);
        await expect(page.locator('.g-overall-progress-message')).toContainText('Selected');
        await page.locator('.g-start-upload').click();
        await waitForIdlePage(page);
        await expect(page.locator('.g-item-count')).toHaveText('1');

        // Drop two files and upload them.
        await page.locator('.g-upload-here-button').click();
        await expect(page.locator('.g-drop-zone')).toBeVisible();
        await page.evaluate((names: string[]) => {
            const dt = new DataTransfer();
            names.forEach((name) => dt.items.add(new File([new Uint8Array(10).fill(98)], name, { type: 'text/plain' })));
            const items = names.map(() => ({ webkitGetAsEntry: () => ({ isFile: true }) }));
            const fake: unknown = { files: dt.files, items };
            const ev = new Event('drop', { bubbles: true, cancelable: true });
            Object.defineProperty(ev, 'dataTransfer', { value: fake });
            document.querySelector('.g-drop-zone')!.dispatchEvent(ev);
        }, ['upload1.tmp', 'upload2.tmp']);
        await expect(page.locator('.g-overall-progress-message')).toContainText('Selected 2 files');
        await page.locator('.g-start-upload').click();
        await waitForIdlePage(page);
        await expect(page.locator('.g-item-count')).toHaveText('3');

        // Dropping a directory is rejected with an error and nothing uploaded.
        await page.locator('.g-upload-here-button').click();
        await expect(page.locator('.g-drop-zone')).toBeVisible();
        await page.evaluate(() => {
            const dt = new DataTransfer();
            dt.items.add(new File([new Uint8Array(10).fill(99)], 'file1', { type: 'text/plain' }));
            const items = [{ webkitGetAsEntry: () => ({ isFile: false }) }];
            const fake: unknown = { files: dt.files, items };
            const ev = new Event('drop', { bubbles: true, cancelable: true });
            Object.defineProperty(ev, 'dataTransfer', { value: fake });
            document.querySelector('.g-drop-zone')!.dispatchEvent(ev);
        });
        await expect(page.locator('.g-upload-error-message')).toContainText('Only files may be uploaded');
        await expect(page.locator('.g-item-count')).toHaveText('3');
        await page.locator('#g-dialog-container .modal-footer a.btn-default').click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();
    });
});

test.describe('Picked resource actions', () => {
    setupServer();

    test('move, copy, and delete picked resources', async ({ page }) => {
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
        const privateId = await getUserFolderId(page, 'Private');
        await createFolderApi(page, 'folder', privateId, 'subA');
        await createFolderApi(page, 'folder', privateId, 'subB');
        await gotoFolder(page, privateId);
        await expect(page.locator('.g-upload-here-button:visible')).toBeVisible();
        await upload(page, path.join(__dirname, 'data', 'testFile.txt'));

        const totalCheckboxes = page.locator('.g-list-checkbox');
        const itemCheckboxes = page.locator('.g-item-list-container .g-list-checkbox');
        await expect(totalCheckboxes).toHaveCount(3);

        // Move the item into subA: pick it, navigate in-SPA into subA, and move.
        await itemCheckboxes.first().click();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await page.locator('a.g-pick-checked').click();
        await expect(page.locator('.g-checked-actions-menu')).toBeHidden();

        await page.locator('a.g-folder-list-link', { hasText: 'subA' }).click();
        await expect(page.locator('.g-empty-parent-message:visible')).toBeVisible();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-move-picked')).toBeVisible();
        await page.locator('a.g-move-picked').click();
        await expect(itemCheckboxes).toHaveCount(1);

        // Back to Private; it should now contain just the two folders.
        await page.locator('a.g-breadcrumb-link', { hasText: 'Private' }).click();
        await expect(totalCheckboxes).toHaveCount(2);

        // Copy both folders into Private, doubling the resources to four.
        await page.locator('.g-select-all').check();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await page.locator('a.g-pick-checked').click();
        await expect(page.locator('.g-checked-actions-menu')).toBeHidden();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-copy-picked')).toBeVisible();
        await page.locator('a.g-copy-picked').click();
        await expect(totalCheckboxes).toHaveCount(4);

        // Upload an item and pick it.  On the user page, copy and move are not
        // offered for items, but the picked resources can be cleared.
        await upload(page, path.join(__dirname, 'data', 'testFile2'));
        await expect(totalCheckboxes).toHaveCount(5);
        await itemCheckboxes.first().click();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await page.locator('a.g-pick-checked').click();
        await expect(page.locator('.g-checked-actions-menu')).toBeHidden();
        await page.locator('a.g-breadcrumb-link').first().click();
        await expect(page.locator('.g-folder-list-link').first()).toBeVisible();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-copy-picked')).toHaveCount(0);
        await expect(page.locator('a.g-move-picked')).toHaveCount(0);
        await expect(page.locator('a.g-clear-picked')).toHaveCount(1);
        await page.locator('a.g-clear-picked').click();
        await expect(page.locator('.g-checked-actions-menu')).toBeHidden();

        // Back into Private and delete all remaining resources.
        await page.locator('a.g-folder-list-link', { hasText: 'Private' }).click();
        await expect(totalCheckboxes).toHaveCount(5);
        await page.locator('.g-select-all').check();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await page.locator('a.g-delete-checked').click();
        await expect(page.locator('#g-confirm-button:visible')).toBeVisible();
        await page.locator('#g-confirm-button').click();
        await expect(page.locator('.g-empty-parent-message:visible')).toBeVisible();
        await expect(totalCheckboxes).toHaveCount(0);
    });
});

test.describe('Resource permissions for a second user', () => {
    setupServer();

    test('a second user cannot move or copy another user\'s resources', async ({ page }) => {
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
        const publicId = await getUserFolderId(page, 'Public');
        await gotoFolder(page, publicId);
        await expect(page.locator('.g-upload-here-button:visible')).toBeVisible();
        await upload(page, path.join(__dirname, 'data', 'testFile.txt'));
        await upload(page, path.join(__dirname, 'data', 'testFile2'));
        await createFolderApi(page, 'folder', publicId, 'pubSub');
        await page.reload();
        await expect(page.locator('.g-list-checkbox')).toHaveCount(3);

        await logout(page);
        await createUser(page, 'janedoe', 'jane.doe@girder.test', 'Jane', 'Doe', 'password!');

        // Navigate to John's user page via quick search.
        const field = page.locator('.g-quick-search-container input.g-search-field');
        await field.fill('john');
        await expect(page.locator('.g-quick-search-container a[data-resource-type="user"]')).toBeVisible();
        await page.locator('.g-quick-search-container a[data-resource-type="user"]').click();
        await waitForIdlePage(page);

        // Only John's Public folder is visible to Jane.
        await expect(page.locator('a.g-folder-list-link', { hasText: 'Public' })).toBeVisible();
        await page.locator('a.g-folder-list-link', { hasText: 'Public' }).click();
        await expect(page.locator('.g-list-checkbox')).toHaveCount(3);

        // Picking an item: no copy or move, but the resources can be cleared.
        await page.locator('.g-item-list-container .g-list-checkbox').first().click();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await page.locator('a.g-pick-checked').click();
        await expect(page.locator('.g-checked-actions-menu')).toBeHidden();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-copy-picked')).toHaveCount(0);
        await expect(page.locator('a.g-move-picked')).toHaveCount(0);
        await expect(page.locator('a.g-clear-picked')).toHaveCount(1);
        await page.locator('a.g-clear-picked').click();
        await expect(page.locator('.g-checked-actions-menu')).toBeHidden();

        // Picking a folder: no copy or move either.
        await page.locator('.g-folder-list-container .g-list-checkbox').first().click();
        await expect(page.locator('.g-checked-actions-button')).not.toBeDisabled();
        await page.locator('.g-checked-actions-button').click();
        await page.locator('a.g-pick-checked').click();
        await expect(page.locator('.g-checked-actions-menu')).toBeHidden();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-copy-picked')).toHaveCount(0);
        await expect(page.locator('a.g-move-picked')).toHaveCount(0);
        await expect(page.locator('a.g-clear-picked')).toHaveCount(1);
        await page.keyboard.press('Escape');

        // Navigate to Jane's own folders.  On the user page itself, copy and
        // move are not offered, but the picked resources can still be cleared.
        await page.locator('.g-user-dropdown-link').click();
        await page.locator('a.g-my-folders').click();
        await expect(page.locator('a.g-folder-list-link', { hasText: 'Private' })).toBeVisible();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-copy-picked')).toHaveCount(0);
        await expect(page.locator('a.g-move-picked')).toHaveCount(0);
        await expect(page.locator('a.g-clear-picked')).toHaveCount(1);
        await page.keyboard.press('Escape');

        // In Jane's own private folder she may copy the picked resources but
        // not move them, because she only has read access to the originals.
        await page.locator('a.g-folder-list-link', { hasText: 'Private' }).click();
        await expect(page.locator('.g-empty-parent-message:visible')).toBeVisible();
        await page.locator('.g-checked-actions-button').click();
        await expect(page.locator('a.g-copy-picked')).toHaveCount(1);
        await expect(page.locator('a.g-move-picked')).toHaveCount(0);
    });
});

test.describe('FileModel static upload functions', () => {
    setupServer();

    test('uploadToFolder and uploadToItem', async ({ page }) => {
        await createUser(page, 'dbowman', 'dbowman@nasa.gov', 'David', 'Bowman', 'jupiter');

        const ids = await page.evaluate(async () => {
            // @ts-ignore - window.girder is available at runtime
            const Folder = window.girder.models.FolderModel;
            // @ts-ignore - window.girder is available at runtime
            const Item = window.girder.models.ItemModel;
            // @ts-ignore - window.girder is available at runtime
            const me = window.girder.auth.getCurrentUser().get('_id');
            const folder = await new Promise<{ get: (k: string) => string }>((resolve, reject) => {
                const f = new Folder({ parentType: 'user', parentId: me, name: 'top level folder' });
                f.on('g:saved', () => resolve(f));
                f.on('g:error', reject);
                f.save();
            });
            const item = await new Promise<{ get: (k: string) => string }>((resolve, reject) => {
                const i = new Item({ folderId: folder.get('_id'), name: 'an item' });
                i.on('g:saved', () => resolve(i));
                i.on('g:error', reject);
                i.save();
            });
            return { folderId: folder.get('_id'), itemId: item.get('_id') };
        });

        // uploadToFolder: the file lands in an item named after the file.
        const halSpeech = "Just what do you think you're doing, Dave?";
        const halFileId = await page.evaluate(async (args: { folderId: string, speech: string }) => {
            // @ts-ignore - window.girder is available at runtime
            const File = window.girder.models.FileModel;
            const fm = new File();
            await new Promise<void>((resolve, reject) => {
                fm.on('g:upload.complete', () => resolve());
                fm.on('g:error', reject);
                fm.uploadToFolder(args.folderId, args.speech, 'hal.txt', 'text/plain');
            });
            return fm.id as string;
        }, { folderId: ids.folderId, speech: halSpeech });

        const halItems = await api(page, {
            url: '/item',
            method: 'GET',
            data: { folderId: ids.folderId, text: 'hal.txt' },
        }) as { _id: string }[];
        const halFiles = await api(page, { url: `/item/${halItems[0]._id}/files`, method: 'GET' }) as { _id: string, name: string }[];
        expect(halFiles[0]._id).toBe(halFileId);
        expect(halFiles[0].name).toBe('hal.txt');
        const halText = await api(page, {
            url: `/file/${halFiles[0]._id}/download`,
            method: 'GET',
            dataType: 'text',
        });
        expect(halText).toBe(halSpeech);

        // uploadToItem: the file lands in the given item.
        const daveSpeech = 'Open the pod bay doors, HAL.';
        const daveFileId = await page.evaluate(async (args: { itemId: string, speech: string }) => {
            // @ts-ignore - window.girder is available at runtime
            const File = window.girder.models.FileModel;
            const fm = new File();
            await new Promise<void>((resolve, reject) => {
                fm.on('g:upload.complete', () => resolve());
                fm.on('g:error', reject);
                fm.uploadToItem(args.itemId, args.speech, 'dave.txt', 'text/plain');
            });
            return fm.id as string;
        }, { itemId: ids.itemId, speech: daveSpeech });

        const daveFiles = await api(page, { url: `/item/${ids.itemId}/files`, method: 'GET' }) as { _id: string, name: string }[];
        expect(daveFiles[0]._id).toBe(daveFileId);
        expect(daveFiles[0].name).toBe('dave.txt');
        const daveText = await api(page, {
            url: `/file/${daveFiles[0]._id}/download`,
            method: 'GET',
            dataType: 'text',
        });
        expect(daveText).toBe(daveSpeech);
    });
});
