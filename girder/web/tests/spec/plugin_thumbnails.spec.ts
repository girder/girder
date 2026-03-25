import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, upload } from '../util';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Test the thumbnails front-end', () => {
    setupServer();

    test('create and delete a thumbnail', async ({ page }) => {
        await createUser(page, 'admin');

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.getByRole('link', { name: ' My folders' }).click();
        await page.getByRole('link', { name: ' Private ' }).click();
        await upload(page, path.join(__dirname, '..', '..', 'public', 'Girder_Mark.png'));

        await page.getByRole('link', { name: ' Girder_Mark.png' }).click();
        await page.getByTitle('Create thumbnail of this file').click();
        await page.getByPlaceholder('width').fill('50');
        await page.getByPlaceholder('width').press('Tab');
        await page.getByPlaceholder('height').fill('50');
        await page.getByRole('button', { name: ' Create' }).click();

        await expect(page.locator('.g-thumbnail')).toBeVisible();

        await page.getByTitle('Delete', { exact: true }).click();
        await page.getByText('Delete', { exact: true }).click();

        await expect(page.locator('.g-thumbnail')).not.toBeVisible();

        // Make sure the thumbnail creation task appears in the job list.
        // (Really we are just using this to test the jobs front-end, because this conveniently
        // creates a job, which is otherwise tricky in testing.)
        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.getByRole('link', { name: ' My jobs' }).click();

        await page.getByText('Timing history').click();
        await expect(page.locator('.g-jobs-graph svg')).toBeVisible();
        await page.getByText('List').click();
        await page.getByRole('link', { name: 'Generate thumbnail for Girder_Mark.png' }).click();
        await expect(page.locator('.g-job-status-badge')).toContainText('Success');
    });
});
