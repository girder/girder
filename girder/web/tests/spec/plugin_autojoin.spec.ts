import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, waitForIdlePage } from '../util';

/**
 * Ported from 3.x-maintenance: plugins/autojoin/plugin_tests/autojoinSpec.js
 * Tests for the Auto Join plugin's configuration page and its effect on new
 * users.
 */

/**
 * Navigate to the groups list page.
 */
async function gotoGroupsPage(page: Page) {
    await page.locator('a.g-nav-link[g-target="groups"]').click();
    await expect(page.locator('.g-group-search-form .g-search-field')).toBeVisible();
}

/**
 * Create a private group and wait for its page to load. Assumes the user is
 * logged in.
 */
async function createGroup(page: Page, name: string) {
    await gotoGroupsPage(page);
    await expect(page.locator('.g-group-create-button')).toBeVisible();
    await page.locator('.g-group-create-button').click();
    await expect(page.locator('#g-name')).toBeVisible();
    await page.locator('#g-name').fill(name);
    await page.locator('.g-save-group').click();
    await waitForIdlePage(page);
    await expect(page.locator('.g-group-name')).toHaveText(name);
}

/**
 * Navigate to the Auto Join plugin configuration page.
 */
async function gotoAutojoinConfig(page: Page) {
    await page.locator('a.g-nav-link[g-target="admin"]').click();
    await page.locator('.g-plugins-config').click();
    const configLink = page.locator('.g-plugin-list-item[data-name="autojoin"] a.g-plugin-config-link');
    await expect(configLink).toBeVisible();
    await configLink.click();
    // Wait for the group collection to populate the group select.
    await expect(page.locator('#g-autojoin-group > option')).toHaveCount(4);
}

/**
 * Fill out and submit the "add rule" row of the Auto Join configuration page.
 */
async function addRule(page: Page, pattern: string, groupName: string, level: string) {
    await page.locator('#g-autojoin-pattern').fill(pattern);
    await page.locator('#g-autojoin-group').selectOption({ label: groupName });
    await page.locator('#g-autojoin-level').selectOption(level);
    await page.locator('#g-autojoin-add').click();
}

test.describe('Test the auto join plugin', () => {
    setupServer();

    test('configure auto join rules', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Joe', 'Admin', 'password');

        await createGroup(page, 'group1');
        await createGroup(page, 'group2');
        await createGroup(page, 'group3');

        await gotoAutojoinConfig(page);

        await addRule(page, '@girder1.test', 'group1', '2');
        await addRule(page, '@girder2.test', 'group2', '1');
        await addRule(page, '@girder2.test', 'group3', '0');

        await expect(page.locator('.g-autojoin-container tbody tr')).toHaveCount(3);
        await expect(page.locator('.g-autojoin-container')).toContainText('@girder1.test');
        await expect(page.locator('.g-autojoin-container')).toContainText('@girder2.test');

        await page.locator('#g-autojoin-save').click();
        await expect(page.locator('#g-alerts-container')).toContainText('Settings saved');
        await waitForIdlePage(page);
    });

    test('auto join a user whose email matches the girder2 rule', async ({ page }) => {
        await createUser(page, 'user1', 'user1@girder2.test', 'Joe', 'User', 'password');

        await gotoGroupsPage(page);
        await expect(page.locator('.g-group-title', { hasText: 'group1' })).toHaveCount(0);
        await expect(page.locator('.g-group-title', { hasText: 'group2' })).toHaveCount(1);
        await expect(page.locator('.g-group-title', { hasText: 'group3' })).toHaveCount(1);
    });

    test('auto join a user whose email matches the girder1 rule', async ({ page }) => {
        await createUser(page, 'user2', 'user2@girder1.test', 'Joe', 'User', 'password');

        await gotoGroupsPage(page);
        await expect(page.locator('.g-group-title', { hasText: 'group1' })).toHaveCount(1);
        await expect(page.locator('.g-group-title', { hasText: 'group2' })).toHaveCount(0);
        await expect(page.locator('.g-group-title', { hasText: 'group3' })).toHaveCount(0);
    });
});
