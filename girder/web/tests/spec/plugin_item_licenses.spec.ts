import { expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser } from '../util';

test.describe('Test the item licenses front-end', () => {
    setupServer();

    test('test setting and viewing an item license', async ({ page }) => {
        await createUser(page, 'admin');

        await page.locator('#g-app-header-container').getByText('admin').click();
        await page.getByRole('link', { name: ' My folders' }).click();

        await page.getByRole('link', { name: ' Public ' }).click();
        await page.getByRole('button', { name: ' ' }).click();
        await page.getByRole('menuitem', { name: ' Create item here' }).click();

        await page.getByPlaceholder('Enter item name').fill('License test');
        await page.getByRole('combobox', { name: 'License' }).selectOption('The MIT License (MIT)');
        await page.getByRole('button', { name: ' Create' }).click();

        await page.getByRole('link', { name: ' License test' }).click();
        await expect(page.locator('.g-item-license.g-info-list-entry')).toContainText('The MIT License (MIT)');
    });
});
