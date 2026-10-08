import { Locator, Page, expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, login, logout } from '../util';

/**
 * Ported from 3.x-maintenance: plugins/homepage/plugin_tests/homepageSpec.js
 * Tests for the Homepage plugin's configuration page and its effect on the
 * front page.
 */

const markdown =
    'It\'s very easy to make some words **bold** and other words *italic* with ' +
    'Markdown. You can even [link to Girder!](https://girder.readthedocs.io/)';

/**
 * Assert that the given container renders the expected markdown content.
 */
async function expectMarkdown(container: Locator) {
    await expect(container.locator('p')).toContainText("It's very easy");
    await expect(container.locator('strong')).toContainText('bold');
    await expect(container.locator('em')).toContainText('italic');
    await expect(container.locator('a[href="https://girder.readthedocs.io/"]')).toContainText('link to Girder!');
}

/**
 * Navigate to the Homepage plugin configuration page.
 */
async function gotoHomepageConfig(page: Page) {
    await page.locator('a.g-nav-link[g-target="admin"]').click();
    await page.locator('.g-plugins-config').click();
    const configLink = page.locator('.g-plugin-list-item[data-name="homepage"] a.g-plugin-config-link');
    await expect(configLink).toBeVisible();
    await configLink.click();
    await expect(page.locator('.g-homepage-container')).toBeVisible();
}

/**
 * Navigate back to the front page via the app title.
 */
async function gotoFrontPage(page: Page) {
    await page.locator('.g-app-title').click();
}

/**
 * Save the homepage configuration form and wait for the success alert.
 */
async function saveHomepageConfig(page: Page) {
    await page.locator('#g-homepage-form input[type="submit"]').click();
    await expect(page.locator('#g-alerts-container')).toContainText('Settings saved');
}

test.describe('Test the homepage front-end', () => {
    setupServer();

    test('exercise homepage markdown customization', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Mark', 'Down', 'password');

        await gotoHomepageConfig(page);

        // Write markdown and verify the preview renders it.
        await page.locator('.g-homepage-container textarea.g-markdown-text').fill(markdown);
        await page.locator('.g-homepage-container a.g-preview-link').click();
        await expectMarkdown(page.locator('.g-homepage-container .g-markdown-preview'));

        await saveHomepageConfig(page);

        // The front page body is completely replaced by the rendered markdown.
        await gotoFrontPage(page);
        await expectMarkdown(page.locator('#g-app-body-container'));
    });

    test('set, preview, and save welcome text and branding', async ({ page }) => {
        await login(page, 'admin', 'password');

        await gotoHomepageConfig(page);

        // Clear the full-page markdown so the branding settings are used.
        await page.locator('.g-homepage-container textarea.g-markdown-text').fill('');
        await page.locator('.g-homepage-container a.g-preview-link').click();
        await expect(page.locator('.g-homepage-container .g-markdown-preview')).toHaveText('Nothing to show');

        // Set header, subheader, and welcome text.
        await page.locator('#g-homepage-header').fill('Header');
        await page.locator('#g-homepage-subheader').fill('Subheader');
        const welcomeText = page.locator('.g-homepage-welcome-text-container textarea.g-markdown-text');
        await welcomeText.fill(markdown);
        await page.locator('.g-homepage-welcome-text-container a.g-preview-link').click();
        await expectMarkdown(page.locator('.g-homepage-welcome-text-container .g-markdown-preview'));

        await saveHomepageConfig(page);

        // The branded front page shows the configured header/subheader and the
        // welcome text rendered as markdown.
        await gotoFrontPage(page);
        await expect(page.locator('.g-frontpage-title')).toHaveText('Header');
        await expect(page.locator('.g-frontpage-subtitle')).toHaveText('Subheader');
        await expectMarkdown(page.locator('.g-frontpage-welcome-text-content'));
    });

    test('settings persist after reload and are visible anonymously', async ({ page }) => {
        await login(page, 'admin', 'password');

        // Configure the full-page markdown replacement.
        await gotoHomepageConfig(page);
        await page.locator('.g-homepage-container textarea.g-markdown-text').fill(markdown);
        await saveHomepageConfig(page);

        // Re-open the config page and verify the markdown was persisted.
        await gotoHomepageConfig(page);
        await expect(page.locator('.g-homepage-container textarea.g-markdown-text')).toHaveValue(markdown);

        // Log out and verify the markdown still renders to anonymous users.
        await logout(page);
        await gotoFrontPage(page);
        await expectMarkdown(page.locator('#g-app-body-container'));
    });
});
