import { expect, Page } from '@playwright/test';

export const waitForDialog = async (page: Page) => {
  await expect(page.locator('#g-dialog-container')).toBeVisible();
  await expect(page.locator('.modal-backdrop')).toBeVisible();
  await delay(500);
  // @ts-ignore
  // while (await page.evaluate(() => window.girder._inTransition)) {
  //   await delay(100);
  // }
//   waitsFor(function () {
//     return !girder._inTransition;
// }, 'dialog transitions to finish');
// waitsFor(function () {
//     return girder.rest.numberOutstandingRestRequests() === 0;
// }, 'dialog rest requests to finish' + desc);
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
  await page.locator('#g-login').fill(login, { timeout: 1000 });
  await page.locator('#g-email').fill(email, { timeout: 1000 });
  await page.locator('#g-firstName').fill(firstName, { timeout: 1000 });
  await page.locator('#g-lastName').fill(lastName, { timeout: 1000 });
  await page.locator('#g-password').fill(password, { timeout: 1000 });
  await page.locator('#g-password2').fill(password, { timeout: 1000 });
  await page.locator('#g-register-button').click();
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
  await page.locator('#g-login').fill(login, { timeout: 1000 });
  await page.locator('#g-password').fill(password, { timeout: 1000 });
  await page.locator('#g-login-button').click();
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
    await expect(page.locator('.g-start-upload')).toBeHidden();
  }
};
