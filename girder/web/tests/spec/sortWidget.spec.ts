import { Page, expect, test } from '@playwright/test';

import { createUser, login, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/sortWidgetSpec.js
 *
 * Tests the SortCollectionWidget as rendered on the users page: the default
 * sort order, toggling the sort direction with the order button, and sorting
 * by a chosen field via the sort field dropdown.  The original spec used a
 * single sequential Jasmine describe; this port keeps that sequence in a
 * serial Playwright describe so each test gets a fresh page while the server
 * and database are shared.
 */

/** Navigate to the users list page and wait for it to finish loading. */
async function goToUsersPage(page: Page) {
    await expect(page.locator('a.g-nav-link[g-target="users"]:visible')).toBeVisible();
    await page.locator('a.g-nav-link[g-target="users"]').click();
    await expect(page.locator('.g-user-search-form .g-search-field:visible')).toBeEnabled();
    await waitForIdlePage(page);
}

/** Return the displayed user names, in list order. */
async function userNames(page: Page) {
    const texts = await page.locator('a.g-user-link').allTextContents();
    return texts.map((text) => text.trim());
}

test.describe('Sort user list', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('register a user (first is admin)', async ({ page }) => {
        await createUser(
            page,
            'admin',
            'admin@girder.test',
            'BFirstName',
            'BLastName',
            'adminpassword!',
        );
    });

    test('register another user', async ({ page }) => {
        await createUser(
            page,
            'nonadmin',
            'nonadmin@girder.test',
            'CFirstName',
            'CLastName',
            'password!',
        );
    });

    test('register third user', async ({ page }) => {
        await createUser(
            page,
            'nonadmin2',
            'nonadmin2@girder.test',
            'AFirstName',
            'ALastName',
            'password!',
        );
    });

    test('view the users on the user page and try different sort options', async ({ page }) => {
        // In the original spec the third registration left that user logged
        // in; the users page is only reachable from the nav when logged in.
        await login(page, 'nonadmin2', 'password!');
        await goToUsersPage(page);

        await expect(page.locator('.g-user-list-entry')).toHaveCount(3);

        // The default sort is by last name, ascending.
        await expect.poll(() => userNames(page)).toEqual([
            'AFirstName ALastName',
            'BFirstName BLastName',
            'CFirstName CLastName',
        ]);

        // Clicking the visible sort order icon toggles the direction.  The
        // widget re-renders once the refetched collection arrives, at which
        // point the descending icon is the visible one.
        await page.locator('.g-user-sort a.g-sort-order-button:not(.hide)').click();
        await expect(page.locator('.g-user-sort a.g-sort-order-button.g-down:not(.hide)')).toBeVisible();

        await expect.poll(() => userNames(page)).toEqual([
            'CFirstName CLastName',
            'BFirstName BLastName',
            'AFirstName ALastName',
        ]);

        // Open the sort field dropdown and sort by creation date.  Choosing
        // a field does not reset the direction, which is still descending
        // from the toggle above, so the most recently created user is first.
        await page.locator('.g-user-sort .g-collection-sort-actions').click();
        const menu = page.locator('.g-user-sort .g-collection-sort-menu');
        await expect(menu).toBeVisible();
        const creationDateLink = menu.locator('a.g-collection-sort-link', { hasText: 'Creation Date' });
        await expect(creationDateLink).toHaveCount(1);
        await creationDateLink.click();

        await expect.poll(() => userNames(page)).toEqual([
            'AFirstName ALastName',
            'CFirstName CLastName',
            'BFirstName BLastName',
        ]);
        await waitForIdlePage(page);
    });
});
