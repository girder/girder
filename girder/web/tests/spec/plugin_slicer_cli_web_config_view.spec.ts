import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, waitForIdlePage } from '../util';

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

test.describe('Slicer CLI web config view', () => {
    setupServer();

    test('change the slicer_cli_web task folder setting', async ({ page }) => {
        await createUser(page, 'admin');
        await waitForIdlePage(page);

        const me = await asyncRestRequest(page, { url: '/user/me' }) as any;
        const folder = await asyncRestRequest(page, {
            url: '/folder',
            method: 'POST',
            data: { name: 'Task Folder', parentType: 'user', parentId: me._id },
        }) as any;
        await waitForIdlePage(page);

        // Navigate to the plugin's admin settings page.
        await page.getByRole('link', { name: ' Admin console' }).click();
        await page.getByRole('link', { name: ' Plugins' }).click();
        const configLink = page.locator('.g-plugin-config-link[g-route="plugins/slicer_cli_web/config"]');
        await expect(configLink).toBeVisible();
        await configLink.click();

        await expect(page.locator('#g-slicer-cli-web-form input#g-slicer-cli-web-upload-folder')).toBeVisible();

        // Fill in the created folder and save.
        await page.locator('#g-slicer-cli-web-upload-folder').fill(folder._id);
        await expect(page.locator('#g-slicer-cli-web-upload-folder')).toHaveValue(folder._id);

        // Save the settings.
        await page.locator('#g-slicer-cli-web-form input.btn-primary').click();
        await waitForIdlePage(page);

        const settings = await asyncRestRequest(page, {
            url: '/system/setting',
            method: 'GET',
            data: { list: JSON.stringify(['slicer_cli_web.task_folder']) },
        }) as any;
        expect(settings['slicer_cli_web.task_folder']).toBe(folder._id);
    });
});
