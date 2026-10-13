import path from 'path';
import { fileURLToPath } from 'url';

import { Page, expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload, waitForIdlePage } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Make a REST request from within the page context and await its result.
 */
async function asyncRestRequest(page: Page, opts: Record<string, unknown>) {
    return await page.evaluate((requestOpts) => {
        return new Promise((resolve, reject) => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.rest.restRequest(requestOpts).done((resp: unknown) => {
                resolve(resp);
            }).fail((resp: unknown) => {
                reject(resp);
            });
        });
    }, opts);
}

test.describe('Test the hashsum download front-end', () => {
    setupServer();

    test('verify presence of key file', async ({ page }) => {
        await createUser(page, 'admin');
        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.locator('a.g-my-folders').click();
        await page.getByRole('link', { name: ' Private ' }).click();
        await upload(page, path.join(__dirname, 'data', 'ten_byte_file.txt'));

        await page.getByRole('link', { name: ' ten_byte_file.txt' }).click();
        await page.getByTitle('Show info').click();
        await expect(page.locator('input.g-hash-textbox').first()).toHaveValue('ff3245abe317049ed1b8aa7aa2f4c4dcb8bf86f083ed67eb26b43e2fbe3ba8fdf759f9e2f46fcf2a06c2dfeddf0cedcd41a68034cd618b880785b34f759d1a69')
    });
});

test.describe('Test the hashsum download configuration page', () => {
    setupServer();

    test('enable automatic checksum computation', async ({ page }) => {
        await createUser(page, 'admin');

        // Navigate to the plugin's admin settings page.
        await page.locator('a.g-nav-link[g-target="admin"]').click();
        await page.locator('.g-plugins-config').click();
        const configLink = page.locator('.g-plugin-list-item[data-name="hashsum_download"] a.g-plugin-config-link');
        await expect(configLink).toBeVisible();
        await configLink.click();

        const autoCompute = page.locator('#g-hashsum-download-auto-compute');
        await expect(autoCompute).toBeVisible();
        await expect(autoCompute).not.toBeChecked();
        await autoCompute.check();

        await page.locator('#g-hashsum-download-config-form input[type="submit"]').click();
        await expect(page.locator('#g-alerts-container')).toContainText('Settings saved');
        await waitForIdlePage(page);

        // Verify that the setting was persisted on the server.
        const settings = await asyncRestRequest(page, {
            url: '/system/setting',
            method: 'GET',
            data: { list: JSON.stringify(['hashsum_download.auto_compute']) },
        }) as Record<string, unknown>;
        expect(settings['hashsum_download.auto_compute']).toBe(true);
    });
});
