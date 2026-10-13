import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, login, logout, waitForDialog, waitForIdlePage } from '../util';

test.describe('Test the terms front-end', () => {
    setupServer();

    test('set the terms', async ({ page }) => {
        await createUser(page, 'admin');
        await page.getByRole('link', { name: ' Collections' }).click();
        await page.getByRole('button', { name: ' Create collection' }).click();
        await page.getByPlaceholder('Enter collection name').fill('Collection with terms');

        await page.getByPlaceholder('Enter collection Terms of Use').fill('# Sample terms');

        await page.getByRole('button', { name: ' Create', exact: true }).click();

        await expect(page.locator('#g-dialog-container')).toBeHidden();
        // Wait for REST requests to complete before further actions
        await waitForIdlePage(page);

        await page.getByRole('button', { name: '' }).click();
        await page.getByLabel('Public — Anyone can view this collection').check();
        await page.getByRole('button', { name: ' Save' }).click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();

        await logout(page);
    });

    test('accept the terms', async ({ page }) => {
        await page.getByRole('link', { name: ' Collections' }).click();
        await page.locator('a').filter({ hasText: 'Collection with terms' }).click();
        await expect(page.locator('h1')).toHaveText('Sample terms');
        await page.getByRole('button', { name: 'I Accept' }).click();
        await expect(page.locator('.g-hierarchy-widget')).toBeVisible();
    });
});

/**
 * Ported from 3.x-maintenance: plugins/terms/plugin_tests/termsSpec.js
 *
 * The original spec was a single sequential Jasmine suite. It is ported here
 * as one Playwright test because the steps depend on each other and on browser
 * localStorage state (anonymous terms acceptance), which does not persist
 * between Playwright tests (each test gets a fresh browser context).
 */
test.describe('Test the terms front-end (full port from 3.x)', () => {
    setupServer();

    test('exercise the complete terms workflow', async ({ page }) => {
        // Create an admin user.
        await createUser(page, 'rocky', 'rocky@phila.pa.us', 'Robert', 'Balboa', 'adrian');

        // Allow all users to create collections.
        await page.evaluate(async () => {
            await new Promise<void>((resolve, reject) => {
                // @ts-ignore - window.girder is available at runtime
                window.girder.rest.restRequest({
                    url: 'system/setting',
                    method: 'PUT',
                    data: {
                        key: 'core.collection_create_policy',
                        value: JSON.stringify({ groups: [], open: true, users: [] }),
                    },
                }).done(() => resolve()).fail((resp: unknown) => reject(resp));
            });
        });
        await waitForIdlePage(page);

        await logout(page);

        // Create a non-admin user to own the test collections.
        await createUser(page, 'creed', 'creed@la.ca.us', 'Apollo', 'Creed', 'the1best');

        // Ensure that basic collections (without terms) still work.
        await page.locator('a.g-nav-link[g-target="collections"]').click();
        await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
        await expect(page.locator('.g-collection-list-entry')).toHaveCount(0);

        await page.locator('.g-collection-create-button').click();
        await waitForDialog(page);
        await page.locator('#g-name').fill('Basic Collection');
        await page.locator('#collection-description-write .g-markdown-text').fill('Some description.');
        await page.locator('.g-save-collection').click();
        await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText('Basic Collection');
        await waitForIdlePage(page);

        // Navigate to the user's folders and into the Public folder.
        await page.locator('.g-user-dropdown-link').click();
        await page.locator('a.g-my-folders').click();
        await expect(page.locator('.g-user-header')).toBeVisible();
        await expect(page.locator('a.g-folder-list-link', { hasText: 'Public' })).toBeVisible();
        await page.locator('a.g-folder-list-link', { hasText: 'Public' }).click();
        await expect(page.locator('.g-item-count-container:visible')).toHaveCount(1);
        await expect(page.locator('.g-hierarchy-breadcrumb-bar .breadcrumb .active')).toHaveText('Public');
        await waitForIdlePage(page);

        // Create an item in the Public folder.
        await page.locator('.g-folder-actions-button:visible').click();
        await page.locator('a.g-create-item:visible').click();
        await waitForDialog(page);
        await page.locator('#g-name').fill('User Item');
        await page.locator('.g-save-item').click();
        await expect(page.locator('a.g-item-list-link', { hasText: 'User Item' })).toHaveCount(1);
        await waitForIdlePage(page);
        await page.locator('a.g-item-list-link', { hasText: 'User Item' }).click();
        await expect(page.locator('.g-item-header .g-item-name')).toHaveText('User Item');
        await waitForIdlePage(page);

        // Create a collection with terms.
        await page.locator('a.g-nav-link[g-target="collections"]').click();
        await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
        await page.locator('.g-collection-create-button').click();
        await waitForDialog(page);
        await expect(page.locator('#collection-terms-write .g-markdown-text')).toBeVisible();
        await page.locator('#g-name').fill('Terms Collection');
        await page.locator('#collection-description-write .g-markdown-text').fill('Some other description.');
        await page.locator('#collection-terms-write .g-markdown-text')
            .fill('# Sample Terms of Use\n\n**¯\\_(ツ)_/¯**');
        await page.locator('.g-save-collection').click();
        await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText('Terms Collection');
        await waitForIdlePage(page);

        const collectionId = ((await page.evaluate(() => window.location.hash)) as string).split('/')[1];
        expect(collectionId).toMatch(/[0-9a-f]{24}/);

        // Make the collection public.
        await page.locator('.g-collection-actions-button:visible').click();
        await page.locator('.g-collection-access-control:visible').click();
        await waitForDialog(page);
        await page.locator('#g-access-public').click();
        await page.locator('.g-save-access-list').click();
        await waitForIdlePage(page);

        // Check the collection info dialog.
        await page.locator('.g-collection-info-button:visible').click();
        await waitForDialog(page);
        await expect(page.locator('.g-terms-info h1')).toHaveText('Sample Terms of Use');
        await page.locator('#g-dialog-container .modal-header .close').click();
        await waitForIdlePage(page);

        // Create a folder in the collection.
        await page.locator('.g-folder-actions-button:visible').click();
        await page.locator('a.g-create-subfolder:visible').click();
        await waitForDialog(page);
        await page.locator('#g-name').fill('Terms Folder');
        await page.locator('.g-save-folder').click();
        await expect(page.locator('a.g-folder-list-link', { hasText: 'Terms Folder' })).toHaveCount(1);
        await waitForIdlePage(page);

        // Navigate into the new folder.
        await page.locator('a.g-folder-list-link', { hasText: 'Terms Folder' }).click();
        await expect(page.locator('.g-item-count-container:visible')).toHaveCount(1);
        await expect(page.locator('.g-hierarchy-breadcrumb-bar .breadcrumb .active')).toHaveText('Terms Folder');
        await waitForIdlePage(page);
        const folderRoute = ((await page.evaluate(() => window.location.hash)) as string).slice(1);

        // Create an item in the folder.
        await page.locator('.g-folder-actions-button:visible').click();
        await page.locator('a.g-create-item:visible').click();
        await waitForDialog(page);
        await page.locator('#g-name').fill('Terms Item');
        await page.locator('.g-save-item').click();
        await expect(page.locator('a.g-item-list-link', { hasText: 'Terms Item' })).toHaveCount(1);
        await waitForIdlePage(page);
        await page.locator('a.g-item-list-link', { hasText: 'Terms Item' }).click();
        await expect(page.locator('.g-item-header .g-item-name')).toHaveText('Terms Item');
        await waitForIdlePage(page);
        const itemRoute = ((await page.evaluate(() => window.location.hash)) as string).slice(1);

        // Navigate in-app without reloading the page.
        const navigate = (route: string) => page.evaluate((r) => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.router.navigate(r, { trigger: true });
        }, route);

        await logout(page);

        // Anonymous users who reject the terms are sent to the front page.
        await navigate(`collection/${collectionId}`);
        await expect(page.locator('.g-terms-container')).toBeVisible();
        await expect(page.locator('.g-terms-info h1')).toHaveText('Sample Terms of Use');
        await page.locator('#g-terms-reject').click();
        await expect(page.locator('.g-frontpage-header')).toBeVisible();

        // Anonymous users must accept the terms before viewing the collection.
        // The original spec cleared localStorage before each of these tests.
        await page.evaluate(() => window.localStorage.clear());
        await navigate(`collection/${collectionId}`);
        await expect(page.locator('.g-terms-container')).toBeVisible();
        await expect(page.locator('.g-terms-info h1')).toHaveText('Sample Terms of Use');
        await page.locator('#g-terms-accept').click();
        await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText('Terms Collection');
        await waitForIdlePage(page);

        // The same applies to folders within the collection.
        await page.evaluate(() => window.localStorage.clear());
        await navigate(folderRoute);
        await expect(page.locator('.g-terms-container')).toBeVisible();
        await expect(page.locator('.g-terms-info h1')).toHaveText('Sample Terms of Use');
        await page.locator('#g-terms-accept').click();
        await expect(page.locator('.g-item-count-container:visible')).toHaveCount(1);
        await expect(page.locator('.g-hierarchy-breadcrumb-bar .breadcrumb .active')).toHaveText('Terms Folder');
        await waitForIdlePage(page);

        // And to items within the collection.
        await page.evaluate(() => window.localStorage.clear());
        await navigate(itemRoute);
        await expect(page.locator('.g-terms-container')).toBeVisible();
        await expect(page.locator('.g-terms-info h1')).toHaveText('Sample Terms of Use');
        await page.locator('#g-terms-accept').click();
        await expect(page.locator('.g-item-header .g-item-name')).toHaveText('Terms Item');
        await waitForIdlePage(page);

        // Remember the anonymously accepted terms hash for the current terms.
        const storageKey = `terms.collection.${collectionId}`;
        const oldStoredHash = await page.evaluate(
            (key) => window.localStorage.getItem(key), storageKey,
        );
        expect(oldStoredHash).not.toBeNull();

        // Log back in as the collection admin.
        await login(page, 'creed', 'the1best');
        await page.locator('a.g-nav-link[g-target="collections"]').click();
        await expect(page.locator('.g-collection-list-entry')).toHaveCount(2);
        await waitForIdlePage(page);
        await page.locator('.g-collection-link', { hasText: 'Terms Collection' }).click();
        await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText('Terms Collection');
        await waitForIdlePage(page);

        // Edit the collection terms.
        await page.locator('.g-collection-actions-button:visible').click();
        await page.locator('.g-edit-collection:visible').click();
        await waitForDialog(page);
        await expect(page.locator('#collection-terms-write .g-markdown-text')).toBeVisible();
        await page.locator('#collection-terms-write .g-markdown-text')
            .fill('# New Terms of Use\n\nThese have changed.');
        await page.locator('.g-save-collection').click();
        await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText('Terms Collection');
        await waitForIdlePage(page);

        await logout(page);

        // The anonymously stored acceptance is still for the old terms, so it
        // is kept, but it no longer matches the updated terms.
        expect(await page.evaluate((key) => window.localStorage.getItem(key), storageKey)).toBe(oldStoredHash);
        expect(await page.evaluate(() => Object.keys(window.localStorage).filter(
            (key) => key.startsWith('terms.collection.'),
        ).length)).toBe(1);

        // Anonymous users are presented with the updated terms.
        await navigate(`collection/${collectionId}`);
        await expect(page.locator('.g-terms-container')).toBeVisible();
        await expect(page.locator('.g-terms-info h1')).toHaveText('New Terms of Use');
        await page.locator('#g-terms-accept').click();
        await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText('Terms Collection');
        await waitForIdlePage(page);

        // Accepting the new terms updates the stored hash.
        expect(await page.evaluate((key) => window.localStorage.getItem(key), storageKey)).not.toBe(oldStoredHash);
    });
});
