import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload, waitForIdlePage } from '../util';

/**
 * Ported from 3.x-maintenance: plugins/readme/plugin_tests/readmeSpec.js
 *
 * Tests that the readme plugin renders a folder's README.md (an item whose name
 * starts with "README") as markdown, and that nothing is rendered when the
 * folder has no README.
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the readme UI', () => {
    setupServer();

    test('render a README.md file', async ({ page }) => {
        await createUser(page, 'myuser');

        // Navigate to the user's Public folder.
        await page.locator('.g-user-dropdown-link').click();
        await page.locator('a.g-my-folders').click();
        await expect(page.locator('a.g-folder-list-link', { hasText: 'Public' })).toBeVisible();
        await page.locator('a.g-folder-list-link', { hasText: 'Public' }).click();
        await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
        await waitForIdlePage(page);

        // With no README in the folder, the widget must not render.
        await expect(page.locator('.g-widget-readme')).toHaveCount(0);

        // Upload a README.md file.
        await upload(page, path.join(__dirname, 'data', 'README.md'));

        // The widget renders and the markdown is displayed.
        await expect(page.locator('.g-widget-readme')).toHaveCount(1);
        await expect(page.locator('.g-widget-readme-header')).toContainText('README');

        const content = page.locator('.g-widget-readme-content');
        await expect(content.locator('h1')).toHaveText('README Testing');
        await expect(content.locator('h2')).toHaveText('Small Header');
        await expect(content.locator('h3')).toHaveText('Smaller header');
        await expect(content.locator('p > code')).toHaveText('A small code block');
        await expect(content.locator('pre code')).toContainText('print("hello, world!")');
        await expect(content.locator('table')).toContainText('Special text! Wow!');
    });
});
