import { test, expect } from '@playwright/test';

// See here how to get started:
// https://playwright.dev/docs/intro
test('page loads with content', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.g-frontpage-subtitle')).toHaveText('Data management platform');
  await expect(page.getByRole('link', { name: 'About' })).toBeVisible();
});
