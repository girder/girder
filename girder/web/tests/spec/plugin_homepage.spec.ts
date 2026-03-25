import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser } from '../util';

test.describe('Test the homepage front-end', () => {
    setupServer();

    test('exercise homepage customization', async ({ page }) => {
        await createUser(page);

        await page.getByRole('link', { name: ' Admin console' }).click();
        await page.getByRole('link', { name: ' Plugins' }).click();

        await page.locator('.g-plugin-list-item[data-name="homepage"] a.g-plugin-config-link').click();

        await page.getByPlaceholder('Enter Markdown for the homepage').fill(
            'It\'s very easy to make some words **bold** and other words *italic* with ' +
            'Markdown. You can even [link to Girder!](https://girder.readthedocs.io/)'
        );

        await page.getByRole('button', { name: 'Save' }).click();
        await expect(page.getByText('× Settings saved.')).toBeVisible();
        await page.getByText('Girder', { exact: true }).click();

        await expect(page.locator('p')).toContainText("It's very easy");
        await expect(page.locator('strong')).toContainText('bold');
        await expect(page.locator('em')).toContainText('italic');
        await expect(page.locator('a[href="https://girder.readthedocs.io/"]')).toContainText('link to Girder!');

        await page.getByRole('link', { name: ' Collections' }).click();
        await page.getByRole('button', { name: ' Create collection' }).click();
        await page.getByPlaceholder('Enter collection name').fill('New collection');
        await page.getByRole('button', { name: ' Create', exact: true }).click();
        await expect(page.getByRole('button', { name: '' })).toBeVisible();
    });
});
