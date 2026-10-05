import { expect, Page } from '@playwright/test';

/**
 * Wait for all outstanding REST requests to complete.
 */
export const waitForIdlePage = async (page: Page) => {
  await expect(page.locator('#g-dialog-container')).toBeHidden();
  await expect(page.locator('.modal-backdrop')).toBeHidden();
  await page.waitForFunction(() => {
    // @ts-ignore
    return window.girder && window.girder.rest && window.girder.rest.numberOutstandingRestRequests() === 0;
  }, { timeout: 10000 });
};

export const waitForDialog = async (page: Page) => {
  await expect(page.locator('#g-dialog-container')).toBeVisible();
  await expect(page.locator('.modal-backdrop')).toBeVisible();
  await page.waitForFunction(() => {
    // @ts-ignore
    return window.girder && window.girder.rest && window.girder.rest.numberOutstandingRestRequests() === 0;
  }, { timeout: 10000 });
};

/**
 * Wait for the given element to become the page's active element.
 *
 * Girder dialogs focus their default field in a Bootstrap `shown.bs.modal`
 * handler, which fires only after the dialog's show transition completes
 * (~300ms after the dialog becomes visible). The dialog views also call
 * focus() during render, but at that point the modal is still hidden, so it
 * has no effect. If we begin filling fields before `shown.bs.modal` fires, a
 * fill that is in flight when the handler runs can be redirected to the newly
 * focused field, corrupting the form (for example, the login field ends up
 * containing the login concatenated with the password). Waiting for the
 * dialog's intended field to be focused guarantees the show transition has
 * finished before any fills are attempted.
 */
export const waitForFocused = async (page: Page, selector: string) => {
  await page.waitForFunction(
    (sel) => document.activeElement === document.querySelector(sel),
    selector,
  );
};

export const logout = async (page: Page) => {
  await page.locator('.g-user-dropdown-link').click();
  await expect(page.locator('.g-logout')).toBeVisible();
  await page.locator('.g-logout').click();
  await expect(page.locator('.g-register')).toBeVisible();
  await expect(page.locator('.g-login')).toBeVisible();
  await expect(page.locator('.g-user-dropdown-link')).toBeHidden();
};

export const createUser = async (
  page: Page,
  login: string = 'firstlast',
  email: string = 'email@email.com',
  firstName: string = 'first',
  lastName: string = 'last',
  password: string = 'password',
) => {
  await expect(page.locator('.g-register')).toBeVisible();
  await page.locator('.g-register').click();
  await waitForDialog(page);
  await expect(page.locator('input#g-email')).toBeVisible();
  await waitForFocused(page, '#g-login');
  await page.locator('#g-login').fill(login, { timeout: 1000 });
  await page.locator('#g-email').fill(email, { timeout: 1000 });
  await page.locator('#g-firstName').fill(firstName, { timeout: 1000 });
  await page.locator('#g-lastName').fill(lastName, { timeout: 1000 });
  await page.locator('#g-password').fill(password, { timeout: 1000 });
  await page.locator('#g-password2').fill(password, { timeout: 1000 });
  await page.locator('#g-register-button').click();
  await waitForIdlePage(page);
  await expect(page.locator('.g-register')).toBeHidden();
  await expect(page.locator('.g-login')).toBeHidden();
  await expect(page.locator('.g-user-dropdown-link')).toBeVisible();
  await expect(page.locator('.g-user-dropdown-link')).toContainText(login);
};

export const login = async (
  page: Page,
  login: string,
  password: string = 'password',
) => {
  await expect(page.locator('.g-login')).toBeVisible();
  await page.locator('.g-login').click();
  await waitForDialog(page);
  await expect(page.locator('#g-login')).toBeVisible();
  await waitForFocused(page, '#g-login');
  await page.locator('#g-login').fill(login, { timeout: 1000 });
  await page.locator('#g-password').fill(password, { timeout: 1000 });
  await page.locator('#g-login-button').click();
  await waitForIdlePage(page);
  await expect(page.locator('.g-register')).toBeHidden();
  await expect(page.locator('.g-login')).toBeHidden();
  await expect(page.locator('.g-user-dropdown-link')).toBeVisible();
  await expect(page.locator('.g-user-dropdown-link')).toContainText(login);
};

export const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const upload = async (page: Page, file: string | string[], awaitSuccess: boolean = true) => {
  // This should be called from a folder view, where the upload button is visible.
  // At the end, the file will be uploaded and you'll be back on the folder view.
  await page.locator('.g-upload-here-button').first().click();
  await expect(page.locator('.g-drop-zone')).toBeVisible();
  await page.locator('#g-files').setInputFiles(file);
  await page.locator('.g-start-upload').click();
  if (awaitSuccess) {
    await waitForIdlePage(page);
    await expect(page.locator('.g-start-upload')).toBeHidden();
  }
};

export const waitForDelete = async (page: Page, container: import('@playwright/test').Locator) => {
  // Click delete on the container and wait for it to disappear and REST requests to complete
  await container.locator('.g-delete').click();
  await expect(page.locator('#g-confirm-button')).toBeVisible();
  await page.locator('#g-confirm-button').click();
  await expect(container).toBeHidden({ timeout: 10000 });
  await waitForIdlePage(page);
};
