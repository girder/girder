import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, logout } from '../util';

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
