import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, logout, waitForIdlePage } from '../util';

async function asyncRestRequest(page: Page, opts: any) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            window.girder.rest.restRequest(opts).done((resp: any) => {
                resolve(resp);
            }).fail((resp: any) => {
                reject(resp);
            });
        });
    }, opts);
}

async function createDefaultTaskFolder(page: Page) {
    const collection = await asyncRestRequest(page, {
        url: '/collection',
        method: 'POST',
        data: { name: 'Tasks', description: 'Default Tasks', public: true },
    }) as any;
    const folder = await asyncRestRequest(page, {
        url: '/folder',
        method: 'POST',
        data: {
            name: 'Slicer CLI Web Tasks',
            parentType: 'collection',
            parentId: collection._id,
            public: true,
        },
    }) as any;
    await asyncRestRequest(page, {
        url: '/system/setting',
        method: 'PUT',
        data: { key: 'slicer_cli_web.task_folder', value: folder._id },
    });
}

async function navigateToCollectionsFolder(page: Page, collectionName: string, folderName: string) {
    await page.locator('a.g-nav-link[g-target="collections"]').click();
    await expect(page.locator('.g-collection-list-entry').first()).toBeVisible();
    await page.locator('.g-collection-link', { hasText: collectionName }).first().click();
    await expect(page.locator('.g-folder-list-link').first()).toBeVisible();
    await page.locator('.g-folder-list-link', { hasText: folderName }).first().click();
    await expect(page.locator('.g-hierarchy-widget').first()).toBeVisible();
}

test.describe('Slicer CLI web upload docker images button', () => {
    setupServer();

    test('the upload CLI task button is visible only for the admin-configured task folder', async ({ page }) => {
        await createUser(page, 'admin');
        await waitForIdlePage(page);
        await createDefaultTaskFolder(page);
        await waitForIdlePage(page);

        await navigateToCollectionsFolder(page, 'Tasks', 'Slicer CLI Web Tasks');

        // The button is visible for an admin in the configured task folder.
        const uploadButton = page.locator('.g-upload-slicer-cli-task-button');
        await expect(uploadButton).toBeVisible();

        // Clicking it opens the upload image dialog.
        await uploadButton.click();
        await expect(page.locator('#g-slicer-cli-web-image')).toBeVisible();
        await page.locator('#g-slicer-cli-web-upload-form button.close').click();
        await expect(page.locator('#g-slicer-cli-web-image')).toBeHidden();

        // A normal user never sees the button.
        await logout(page);
        await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');
        await waitForIdlePage(page);

        await navigateToCollectionsFolder(page, 'Tasks', 'Slicer CLI Web Tasks');
        await expect(page.locator('.g-upload-slicer-cli-task-button')).toHaveCount(0);
    });
});
