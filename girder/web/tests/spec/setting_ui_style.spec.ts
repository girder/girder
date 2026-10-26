import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, waitForDialog } from '../util';

/**
 * Change a setting through the REST API as the logged-in user.
 */
const setSetting = async (page: Page, key: string, value: string) => {
  const girderToken = await page.evaluate(() => window.localStorage.getItem('girderToken'));
  const resp = await page.request.put(new URL('/api/v1/system/setting', page.url()).toString(), {
    headers: { 'Girder-Token': girderToken! },
    form: { key, value },
  });
  expect(resp.ok()).toBeTruthy();
};

const goToMyFolders = async (page: Page, login: string) => {
  await page.locator('#g-app-header-container').getByText(login).click();
  await page.locator('a.g-my-folders').click();
  await expect(page.locator('a.g-folder-list-link', { hasText: 'Private' })).toBeVisible();
};

/**
 * The theme colors the htk style derives from the default banner color
 * (#3F3B3B, which is hsl(0, 3%, 24%)).
 */
const themeColorVariables = async (page: Page) => page.evaluate(() => {
  const style = getComputedStyle(document.documentElement);
  return ['h', 's', 'l'].map((c) => style.getPropertyValue(`--primary-${c}`).trim());
});

test.describe('Test the UI style setting: classic', () => {
  setupServer();

  test('classic style is the default', async ({ page }) => {
    await createUser(page, 'admin');

    await expect(page.locator('html')).not.toHaveClass(/g-ui-htk/);
    await expect(page.locator('link[data-g-ui-style="htk"]')).toHaveCount(0);
    expect(await themeColorVariables(page)).toEqual(['', '', '']);

    // The classic header is drawn on the banner color and has no navigation links
    await expect(page.locator('.g-header-wrapper')).toHaveCSS('background-color', 'rgb(63, 59, 59)');
    await expect(page.locator('#g-app-header-container').getByRole('link', { name: 'Image Explorer' })).toHaveCount(0);
    await expect(page.locator('#g-app-header-container').getByRole('link', { name: 'Home' })).toHaveCount(0);

    // The classic hierarchy widget uses the bootstrap breadcrumb and has no
    // way up from the top level
    await goToMyFolders(page, 'admin');
    await expect(page.locator('.g-hierarchy-breadcrumb-bar ol.breadcrumb')).toBeVisible();
    await expect(page.locator('.g-hierarchy-level-up')).toHaveCount(0);
    await expect(page.locator('.g-folder-actions-menu>li>a.g-create-subfolder')).toHaveCount(1);
  });
});

test.describe('Test the UI style setting: htk', () => {
  setupServer();

  test('htk style', async ({ page }) => {
    await createUser(page, 'admin');
    await setSetting(page, 'core.ui_style', 'htk');
    await page.reload();

    await expect(page.locator('html')).toHaveClass(/g-ui-htk/);
    // The htk stylesheet is loaded after the core stylesheet, so that it
    // overrides bootstrap where they conflict, and before plugin stylesheets.
    await expect(page.locator('link[data-g-ui-style="htk"]')).toHaveCount(1);
    expect(await page.evaluate(() => {
      const sheets = Array.from(document.head.querySelectorAll('link[rel="stylesheet"]')) as HTMLLinkElement[];
      const htk = sheets.findIndex((link) => link.dataset.gUiStyle === 'htk');
      const core = sheets.findIndex((link) => link.href.includes('/assets/'));
      const plugin = sheets.findIndex((link) => link.hasAttribute('data-g-plugin-stylesheet'));
      return { htk, core, plugin };
    })).toMatchObject({ htk: expect.any(Number), core: expect.any(Number), plugin: expect.any(Number) });
    expect(await page.evaluate(() => {
      const sheets = Array.from(document.head.querySelectorAll('link[rel="stylesheet"]')) as HTMLLinkElement[];
      const htk = sheets.findIndex((link) => link.dataset.gUiStyle === 'htk');
      const core = sheets.findIndex((link) => link.href.includes('/assets/'));
      const plugin = sheets.findIndex((link) => link.hasAttribute('data-g-plugin-stylesheet'));
      return core >= 0 && plugin >= 0 && core < htk && htk < plugin;
    })).toBeTruthy();
    // Tailwind's base layer is in effect
    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(244, 244, 245)');
    expect(await themeColorVariables(page)).toEqual(['0', '3%', '24%']);

    // The htk header is white with navigation links, and highlights the current section
    const header = page.locator('#g-app-header-container');
    await expect(page.locator('.g-header-wrapper')).toHaveCSS('background-color', 'rgb(255, 255, 255)');
    const homeTab = header.getByRole('listitem').filter({ has: page.getByRole('link', { name: 'Home' }) });
    const explorerTab = header.getByRole('listitem').filter({ has: page.getByRole('link', { name: 'Image Explorer' }) });
    await expect(homeTab).toHaveClass(/border-primary/);
    await expect(explorerTab).not.toHaveClass(/border-primary/);
    await header.getByRole('link', { name: 'Image Explorer' }).click();
    await expect(page.locator('.g-collection-create-button')).toBeVisible();
    await expect(explorerTab).toHaveClass(/border-primary/);
    await expect(homeTab).not.toHaveClass(/border-primary/);

    // The htk hierarchy widget has its own breadcrumb bar with child counts
    // and a way up, and lays out the action menus differently
    await goToMyFolders(page, 'admin');
    await expect(page.locator('.g-hierarchy-breadcrumb-bar ol.breadcrumb')).toHaveCount(0);
    await expect(page.locator('.g-hierarchy-breadcrumb-bar .g-hierarchy-level-up')).toBeVisible();
    await expect(page.locator('.g-hierarchy-breadcrumb-bar .g-subfolder-count')).toHaveText('2');

    await page.locator('.g-folder-actions-button:visible').click();
    await page.locator('.g-folder-actions-menu a.g-create-subfolder:visible').click();
    await waitForDialog(page);
    await page.locator('#g-name').fill('htkFolder');
    await page.locator('#g-dialog-container .g-save-folder').click();
    const folderLink = page.locator('a.g-folder-list-link', { hasText: 'htkFolder' });
    await expect(folderLink).toBeVisible();
    await expect(page.locator('.g-hierarchy-breadcrumb-bar .g-subfolder-count')).toHaveText('3');

    // Descend into the folder, where the actions menu offers a download, and
    // come back up
    await folderLink.click();
    await expect(page.locator('.g-hierarchy-breadcrumb-bar a.g-breadcrumb-link', { hasText: 'first last' })).toBeVisible();
    await expect(page.locator('.g-hierarchy-breadcrumb-bar .g-item-count')).toHaveText('0');
    await page.locator('.g-folder-actions-button:visible').click();
    await expect(page.locator('.g-folder-actions-menu a.g-download-folder:visible')).toHaveCount(1);
    await page.keyboard.press('Escape');
    await page.locator('.g-hierarchy-level-up').click();
    await expect(folderLink).toBeVisible();
    await expect(page.locator('.g-hierarchy-breadcrumb-bar a.g-breadcrumb-link')).toHaveCount(0);

    // The checked actions menu
    await page.locator('.g-folder-list-entry', { hasText: 'htkFolder' }).locator('.g-list-checkbox').check();
    await page.locator('.g-checked-actions-button').click();
    await expect(page.locator('.g-checked-actions-menu a.g-download-checked:visible')).toHaveCount(1);
    await expect(page.locator('.g-checked-actions-menu a.g-pick-checked:visible')).toHaveCount(1);
    await page.keyboard.press('Escape');
    // Move off the checked actions button, whose hover tooltip overlaps the
    // "up one level" button
    await page.mouse.move(0, 0);

    // Going up from a user's top level goes to the list of users
    await page.locator('.g-hierarchy-level-up').click();
    await expect(page).toHaveURL(/#users$/);
    await expect(page.locator('.g-user-list-entry', { hasText: 'admin' })).toBeVisible();

    // The download visibility setting is honored by the htk menus
    await setSetting(page, 'core.show_download', 'none');
    await page.reload();
    await goToMyFolders(page, 'admin');
    await page.locator('.g-folder-list-entry', { hasText: 'htkFolder' }).locator('.g-list-checkbox').check();
    await page.locator('.g-checked-actions-button').click();
    await expect(page.locator('.g-checked-actions-menu a.g-pick-checked:visible')).toHaveCount(1);
    await expect(page.locator('.g-checked-actions-menu a.g-download-checked')).toHaveCount(0);
    await page.keyboard.press('Escape');
    await folderLink.click();
    await expect(page.locator('.g-hierarchy-breadcrumb-bar a.g-breadcrumb-link', { hasText: 'first last' })).toBeVisible();
    await page.locator('.g-folder-actions-button:visible').click();
    await expect(page.locator('.g-folder-actions-menu a.g-create-subfolder:visible')).toHaveCount(1);
    await expect(page.locator('.g-folder-actions-menu a.g-download-folder')).toHaveCount(0);
  });
});

test.describe('Test the UI style setting: header navigation label', () => {
  setupServer();

  test('header navigation label setting', async ({ page }) => {
    await createUser(page, 'admin');
    await setSetting(page, 'core.ui_style', 'htk');
    await setSetting(page, 'core.ui_header_nav_label', 'Browse');
    await page.reload();

    const header = page.locator('#g-app-header-container');
    await expect(header.getByRole('link', { name: 'Browse' })).toBeVisible();
    await expect(header.getByRole('link', { name: 'Image Explorer' })).toHaveCount(0);
    await header.getByRole('link', { name: 'Browse' }).click();
    await expect(page.locator('.g-collection-create-button')).toBeVisible();

    // The classic header has no such link, whatever the label
    await setSetting(page, 'core.ui_style', 'classic');
    await page.reload();
    await expect(page.locator('html')).not.toHaveClass(/g-ui-htk/);
    await expect(header.getByRole('link', { name: 'Browse' })).toHaveCount(0);
  });
});

test.describe('Test the UI style setting: system configuration page', () => {
  setupServer();

  test('settings are shown on the system configuration page', async ({ page }) => {
    await createUser(page, 'admin');
    await setSetting(page, 'core.ui_style', 'htk');
    await setSetting(page, 'core.ui_header_nav_label', 'Browse');
    await page.reload();

    await page.getByRole('link', { name: 'Admin console' }).click();
    await page.locator('.g-server-config').click();
    await expect(page.getByText('System configuration')).toBeVisible();
    await expect(page.locator('#g-core-ui-style')).toHaveValue('htk');
    await expect(page.locator('#g-core-ui-style')).toHaveAttribute('disabled');
    await expect(page.locator('#g-core-ui-header-nav-label')).toHaveValue('Browse');
    await expect(page.locator('#g-core-ui-header-nav-label')).toHaveAttribute('disabled');
  });
});
