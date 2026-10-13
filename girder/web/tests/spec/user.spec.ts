import { Page, expect, test } from '@playwright/test';

import { createUser, login, logout, waitForDialog, waitForFocused, waitForIdlePage } from '../util';
import { setupServer, serverLogs } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/userSpec.js
 *
 * Tests user registration, the users page, user settings, password changes
 * and resets, API key management, two-factor authentication, email
 * verification, and account approval. The original spec was a single
 * sequential Jasmine describe sharing a `registeredUsers` list; this port
 * keeps that sequence in serial Playwright describes so each test gets a
 * fresh page while the server and database are shared. Because each describe
 * gets a fresh database, later describes re-create the users they need.
 *
 * System settings are changed through the REST API (as in the ported group
 * spec) because the 5.x settings page is read-only. Emails are read from the
 * server console logs, since the test server runs with
 * GIRDER_EMAIL_TO_CONSOLE enabled.
 */

const ids = {
    admin: '',
    user2: '',
    nonadmin: '',
};

/** The route fragment of the temporary access link sent by email. */
let resetLink = '';

/** Navigate within the single page app (equivalent of girderTest.testRoute). */
async function navigate(page: Page, route: string) {
    await page.evaluate((r) => {
        // @ts-ignore - window.girder is available at runtime
        window.girder.router.navigate(r, { trigger: true });
    }, route);
}

/** Return the id of the currently logged in user. */
async function currentUserId(page: Page): Promise<string> {
    return await page.evaluate(() => {
        // @ts-ignore - window.girder is available at runtime
        return window.girder.auth.getCurrentUser().get('_id');
    });
}

/** Make a REST request from within the page context and await its result. */
async function restRequest(page: Page, opts: Record<string, unknown>) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.rest.restRequest(opts).done((resp: unknown) => {
                resolve(resp);
            }).fail((resp: unknown) => {
                reject(resp);
            });
        });
    }, opts);
}

/** Update a system setting, as the currently logged in (admin) user. */
async function setSetting(page: Page, key: string, value: string) {
    await restRequest(page, {
        url: 'system/setting',
        method: 'PUT',
        data: { key, value },
    });
}

/** Navigate to the users list page. */
async function gotoUsersPage(page: Page) {
    await expect(page.locator('a.g-nav-link[g-target="users"]:visible')).toBeVisible();
    await page.locator('a.g-nav-link[g-target="users"]').click();
    await expect(page.locator('.g-user-search-form .g-search-field:visible')).toBeEnabled();
    await waitForIdlePage(page);
}

/** Open one of the tabs on a user's account page. */
async function openAccountTab(page: Page, id: string, tab: string) {
    await navigate(page, `useraccount/${id}/info`);
    await expect(page.locator('.g-account-tabs')).toBeVisible();
    await waitForIdlePage(page);
    await page.locator(`.g-account-tabs li>a[name="${tab}"]`).click();
    await waitForIdlePage(page);
}

/** Log in as the non-admin user and open their API keys tab. */
async function gotoApiKeysTab(page: Page) {
    await login(page, 'nonadmin', 'newpassword');
    await openAccountTab(page, ids.nonadmin, 'apikeys');
}

/**
 * Create the admin and non-admin users, then set the non-admin's password to
 * 'newpassword' (the state of the users at the end of the first describe).
 */
async function createUsersWithNewPassword(page: Page) {
    await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
    ids.admin = await currentUserId(page);
    await logout(page);
    await createUser(page, 'nonadmin', 'nonadmin@girder.test', 'Not', 'Admin', 'password!');
    ids.nonadmin = await currentUserId(page);
    await logout(page);

    await login(page, 'admin', 'adminpassword!');
    await restRequest(page, {
        url: `user/${ids.nonadmin}/password`,
        method: 'PUT',
        data: { password: 'newpassword' },
    });
    await logout(page);
}

/**
 * Search the captured server output for the temporary access email and return
 * the route fragment of its reset link, e.g. "useraccount/<id>/token/<token>".
 * The email body is a base64-encoded MIME body that is line-wrapped, so for
 * each email in the log, strip the whitespace from everything after the base64
 * transfer-encoding header and decode candidate runs of base64, looking for
 * the anchor tag inside the decoded HTML.
 */
async function fetchResetLink(page: Page, startIndex: number): Promise<string> {
    let link = '';
    await expect.poll(() => {
        const text = serverLogs.slice(startIndex).join('');
        const messages = text.split('Redirecting email to console:').slice(1);
        for (const message of messages) {
            const marker = 'Content-Transfer-Encoding: base64';
            const index = message.indexOf(marker);
            if (index < 0) {
                continue;
            }
            const joined = message.slice(index + marker.length).replace(/\s+/g, '');
            const candidates = joined.match(/[A-Za-z0-9+/=]+/g) ?? [];
            for (const candidate of candidates) {
                if (candidate.length < 60) {
                    continue;
                }
                try {
                    const decoded = Buffer.from(candidate, 'base64').toString('utf8');
                    const hrefIndex = decoded.indexOf('<a href="');
                    if (hrefIndex < 0) {
                        continue;
                    }
                    const href = decoded.slice(hrefIndex + 9);
                    const url = href.slice(0, href.indexOf('"'));
                    const hashIndex = url.indexOf('#');
                    const fragment = hashIndex >= 0 ? url.slice(hashIndex + 1) : '';
                    if (/^useraccount\/[0-9a-f]+\/token\/[A-Za-z0-9]+$/.test(fragment)) {
                        link = fragment;
                    }
                } catch {
                    // Not decodable base64; try the next candidate.
                }
            }
        }
        return link;
    }, { timeout: 30000 }).not.toBe('');
    return link;
}

test.describe('Create an admin and non-admin user', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('register a user (first is admin)', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');

        ids.admin = await currentUserId(page);
    });

    test('create user as admin using dialog', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoUsersPage(page);

        await expect(page.locator('.g-user-create-button')).toHaveCount(1);
        await page.locator('.g-user-create-button').click();
        await waitForDialog(page);
        await expect(page.locator('#g-login')).toBeVisible();
        await waitForFocused(page, '#g-login');
        await page.locator('#g-login').fill('user2');
        await page.locator('#g-email').fill('user2@girder.test');
        await page.locator('#g-firstName').fill('user');
        await page.locator('#g-lastName').fill('2');
        await page.locator('#g-password').fill('password');
        await page.locator('#g-password2').fill('password');

        await page.locator('#g-register-button').click();
        await expect(page.locator('.g-body-title.g-user-name')).toHaveText('user 2');
        await waitForIdlePage(page);

        // Creating a user as an admin should not log the admin out.
        expect(await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            return window.girder.auth.getCurrentUser().get('login');
        })).toBe('admin');

        const hash = await page.evaluate(() => window.location.hash);
        ids.user2 = hash.replace(/^#user\//, '');
        expect(ids.user2).toMatch(/^[0-9a-f]+$/);
    });

    test('logout', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await logout(page);
    });

    test('register another user', async ({ page }) => {
        await createUser(page, 'nonadmin', 'nonadmin@girder.test', 'Not', 'Admin', 'password!');

        ids.nonadmin = await currentUserId(page);
    });

    test('view the users on the user page and click on one', async ({ page }) => {
        await login(page, 'nonadmin', 'password!');
        await gotoUsersPage(page);

        await expect(page.locator('.g-user-list-entry')).toHaveCount(3);
        const names = await page.locator('a.g-user-link').allInnerTexts();
        expect(names.slice().sort()).toEqual(['Admin Admin', 'Not Admin', 'user 2']);

        await page.locator('a.g-user-link', { hasText: 'Admin Admin' }).click();
        await expect(page.locator('.g-user-name')).toHaveText('Admin Admin');
        await waitForIdlePage(page);

        // A non-admin should not see the actions menu on another user's page.
        await expect(page.locator('.g-user-actions-button')).toHaveCount(0);
    });

    test('check for no admin checkbox on user settings page', async ({ page }) => {
        await login(page, 'nonadmin', 'password!');

        await page.locator('.g-user-dropdown-link').click();
        await page.locator('.g-my-settings').click();
        await expect(page.locator('.g-account-tabs')).toBeVisible();
        await waitForIdlePage(page);

        await expect(page.locator('input#g-admin')).toHaveCount(0);
    });

    test('check redirect to front page after logout from user page', async ({ page }) => {
        await login(page, 'nonadmin', 'password!');
        await gotoUsersPage(page);
        await page.locator('a.g-user-link', { hasText: 'Admin Admin' }).click();
        await expect(page.locator('.g-user-name')).toHaveText('Admin Admin');

        await logout(page);
        await expect(page.locator('.g-frontpage-title:visible')).toBeVisible();
    });

    test('check the user count', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoUsersPage(page);
        await expect(page.locator('span.g-user-count')).toHaveText('3');
    });

    test('check redirect to front page after logout from users list page', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoUsersPage(page);

        await logout(page);
        await expect(page.locator('.g-frontpage-title:visible')).toBeVisible();
    });

    test('check for admin checkbox on admin user settings page', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await openAccountTab(page, ids.admin, 'info');

        await expect(page.locator('input#g-admin')).toHaveCount(1);

        // Saving with an empty first name should display a validation error.
        await page.locator('#g-firstName').fill('');
        await page.locator('#g-user-info-form button[type="submit"]').click();
        await expect(page.locator('#g-user-info-error-msg')).toHaveText('First name must not be empty.');

        await page.locator('#g-firstName').fill('Admin');
        await page.locator('#g-user-info-form button[type="submit"]').click();
        await expect(page.locator('#g-user-info-error-msg')).toHaveText('');
    });

    test('test changing other user\'s password', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await navigate(page, `useraccount/${ids.nonadmin}/password`);
        await expect(page.locator('input#g-password-new:visible')).toBeVisible();
        await waitForIdlePage(page);

        await expect(page.locator('.g-user-description')).toHaveText('nonadmin');
        // An admin changing another user's password needs no current password.
        await expect(page.locator('#g-password-old')).toHaveCount(0);

        await page.locator('#g-password-new').fill('a new password');
        await page.locator('#g-password-retype').fill('a new password');
        await page.locator('#g-password-change-form button[type="submit"]').click();

        await expect(page.locator('#g-alerts-container .alert-success')).toBeVisible();
        await expect(page.locator('#g-password-new')).toHaveValue('');
    });

    test('test reset password', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await logout(page);

        await page.locator('.g-login').click();
        await waitForDialog(page);
        await expect(page.locator('input#g-login')).toBeVisible();
        await waitForFocused(page, '#g-login');

        await page.locator('.g-forgot-password').click();
        await expect(page.locator('.g-password-reset-explanation')).toBeVisible();

        await page.locator('#g-email').fill('invalid@girder.test');
        await page.locator('#g-reset-password-button').click();
        await expect(page.locator('#g-dialog-container .g-validation-failed-message'))
            .toContainText('not registered');

        const logStart = serverLogs.length;
        await page.locator('#g-email').fill('nonadmin@girder.test');
        await page.locator('#g-reset-password-button').click();
        await expect(page.locator('.g-password-reset-explanation')).toBeHidden();

        resetLink = await fetchResetLink(page, logStart);
    });

    test('Use reset link', async ({ page }) => {
        await navigate(page, resetLink);
        await expect(page.locator('input#g-password-new:visible')).toBeVisible();
        await expect(page.locator('input#g-password-old:visible')).toHaveCount(0);

        // Mismatched passwords should be rejected.
        await page.locator('#g-password-new').fill('newpassword');
        await page.locator('#g-password-retype').fill('newpassword2');
        await page.locator('#g-password-change-form button[type="submit"]').click();
        await expect(page.locator('#g-password-change-error-msg'))
            .toHaveText('Passwords do not match, try again.');

        // Too-short passwords should be rejected.
        await page.locator('#g-password-new').fill('new');
        await page.locator('#g-password-retype').fill('new');
        await page.locator('#g-password-change-form button[type="submit"]').click();
        await expect(page.locator('#g-password-change-error-msg'))
            .toHaveText('Password must be at least 6 characters long.');

        await page.locator('#g-password-new').fill('newpassword');
        await page.locator('#g-password-retype').fill('newpassword');
        await page.locator('#g-password-change-form button[type="submit"]').click();
        await expect(page.locator('#g-password-new')).toHaveValue('');
    });
});

test.describe('test the API key management tab', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('create an admin and non-admin user', async ({ page }) => {
        await createUsersWithNewPassword(page);
    });

    test('go to the API keys tab', async ({ page }) => {
        await gotoApiKeysTab(page);
        await expect(page.locator('.g-api-keys-empty-message')).toBeVisible();
    });

    test('create a new API key', async ({ page }) => {
        await gotoApiKeysTab(page);

        await page.locator('button.g-api-key-new').click();
        await waitForDialog(page);

        await expect(page.locator('#g-api-key-name')).toBeVisible();
        expect(await page.locator('.g-custom-scope-checkbox').count()).toBeGreaterThan(3);
        await expect(page.locator('#g-scope-mode-full')).toBeChecked();
        await expect(page.locator('#g-scope-mode-custom')).not.toBeChecked();
        expect(await page.locator('.g-custom-scope-checkbox:not(:disabled)').count()).toBe(0);

        await page.locator('#g-api-key-name').fill('test key');

        // Test radio button and checkbox state
        await page.locator('#g-scope-mode-custom').click();
        await expect(page.locator('#g-scope-mode-full')).not.toBeChecked();
        await expect(page.locator('#g-scope-mode-custom')).toBeChecked();
        expect(await page.locator('.g-custom-scope-checkbox:disabled').count()).toBe(0);

        // Saving a custom scope key with no scopes selected should fail.
        await page.locator('.g-save-api-key').click();
        await expect(page.locator('#g-dialog-container .g-validation-failed-message'))
            .toHaveText('Custom scope list must not be empty.');

        await page.locator('.g-custom-scope-checkbox').first().click();
        await page.locator('.g-save-api-key').click();
        await waitForIdlePage(page);
        await expect(page.locator('#g-dialog-container')).toBeHidden();

        const row = page.locator('tr.g-api-key-container');
        await expect(row).toHaveCount(1);
        await expect(row.locator('td[col="name"]')).toHaveText('test key');
        await expect(row.locator('td[col="active"]')).toHaveText('Yes');
        await expect(row.locator('td[col="tokenDuration"]')).toHaveText('Default');
        await expect(row.locator('td[col="scope"]')).toHaveText('Custom scopes');
        await expect(row.locator('td[col="lastUse"]')).toHaveText('Never');
        await expect(row.locator('button.g-api-key-toggle-active.btn-warning')).toHaveCount(1);
    });

    test('edit the API key', async ({ page }) => {
        await gotoApiKeysTab(page);

        await page.locator('button.g-api-key-edit').click();
        await waitForDialog(page);

        await page.locator('#g-api-key-name').fill('new name');
        await page.locator('#g-api-key-token-duration').fill('20');
        await page.locator('#g-scope-mode-full').click();
        await page.locator('.g-save-api-key').click();

        await waitForIdlePage(page);

        const row = page.locator('tr.g-api-key-container');
        await expect(row).toHaveCount(1);
        await expect(row.locator('td[col="name"]')).toHaveText('new name');
        await expect(row.locator('td[col="active"]')).toHaveText('Yes');
        await expect(row.locator('td[col="tokenDuration"]')).toHaveText('20 days');
        await expect(row.locator('td[col="scope"]')).toHaveText('Full access');
        await expect(row.locator('td[col="lastUse"]')).toHaveText('Never');
        await expect(row.locator('button.g-api-key-toggle-active.btn-warning')).toHaveCount(1);
    });

    test('deactivate/reactivate the API key', async ({ page }) => {
        await gotoApiKeysTab(page);

        await page.locator('.g-api-key-toggle-active').click();
        await waitForDialog(page);
        await page.locator('#g-confirm-button').click();
        await waitForIdlePage(page);

        const row = page.locator('tr.g-api-key-container');
        await expect(row).toHaveCount(1);
        await expect(row.locator('td[col="name"]')).toHaveText('new name');
        await expect(row.locator('td[col="active"]')).toHaveText('No');
        await expect(row.locator('td[col="tokenDuration"]')).toHaveText('20 days');
        await expect(row.locator('td[col="scope"]')).toHaveText('Full access');
        await expect(row.locator('td[col="lastUse"]')).toHaveText('Never');
        await expect(row.locator('button.g-api-key-toggle-active.btn-success')).toHaveCount(1);

        await page.locator('.g-api-key-toggle-active').click();
        await expect(page.locator('button.g-api-key-toggle-active.btn-warning')).toHaveCount(1);
    });

    test('delete the API key', async ({ page }) => {
        await gotoApiKeysTab(page);

        await page.locator('.g-api-key-delete').click();
        await waitForDialog(page);
        await page.locator('#g-confirm-button').click();
        await waitForIdlePage(page);

        await expect(page.locator('tr.g-api-key-container')).toHaveCount(0);
        await expect(page.locator('.g-api-keys-empty-message')).toHaveCount(1);
    });
});

test.describe('test the two-factor authentication tab', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('create an admin and non-admin user', async ({ page }) => {
        await createUsersWithNewPassword(page);
    });

    test('go to the two-factor authentication tab', async ({ page }) => {
        await login(page, 'nonadmin', 'newpassword');
        await openAccountTab(page, ids.nonadmin, 'otp');
        await expect(page.locator('.g-account-otp-info-text')).toBeVisible();
    });

    test('begin activation of 2FA', async ({ page }) => {
        await login(page, 'nonadmin', 'newpassword');
        await openAccountTab(page, ids.nonadmin, 'otp');

        await page.locator('#g-user-otp-initialize-enable').click();
        await expect(page.locator('.g-account-otp-enter-manual')).toBeVisible();
    });

    // Further client testing requires a Javascript TOTP implementation, which is too difficult to provide in the
    // current testing environment
});

test.describe('test email verification', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('create an admin and an unverified user', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
        ids.admin = await currentUserId(page);
        await logout(page);
        await createUser(page, 'user2', 'user2@girder.test', 'user', '2', 'password');
        ids.user2 = await currentUserId(page);
        await logout(page);
    });

    test('Turn on email verification', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');

        await page.getByRole('link', { name: 'Admin console' }).click();
        await expect(page.locator('.g-server-config')).toBeVisible();
        await page.locator('.g-server-config').click();
        await expect(page.locator('select#g-core-email-verification')).toBeVisible();

        // The 5.x settings page is read-only, so the setting is changed
        // through the REST API.
        await setSetting(page, 'core.email_verification', 'required');

        await logout(page);
    });

    test('Try to login without verifying email', async ({ page }) => {
        await expect(page.locator('.g-login')).toBeVisible();

        await page.locator('.g-login').click();
        await waitForDialog(page);
        await expect(page.locator('input#g-login')).toBeVisible();
        await waitForFocused(page, '#g-login');

        await page.locator('#g-login').fill('user2');
        await page.locator('#g-password').fill('password');
        await page.locator('#g-login-button').click();

        await expect(page.locator('#g-dialog-container .g-validation-failed-message'))
            .toContainText('Email verification');

        await page.locator('#g-dialog-container a[data-dismiss="modal"]').click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();
    });
});

test.describe('test account approval', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('create an admin and a non-admin user', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');
        ids.admin = await currentUserId(page);
        await logout(page);
        await createUser(page, 'nonadmin', 'nonadmin@girder.test', 'Not', 'Admin', 'newpassword');
        ids.nonadmin = await currentUserId(page);
        await logout(page);
    });

    test('Turn on approval policy', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');

        await page.getByRole('link', { name: 'Admin console' }).click();
        await expect(page.locator('.g-server-config')).toBeVisible();
        await page.locator('.g-server-config').click();
        await expect(page.locator('input#g-core-cookie-lifetime')).toBeVisible();

        // The 5.x settings page is read-only, so the settings are changed
        // through the REST API.
        await setSetting(page, 'core.registration_policy', 'approve');
        await setSetting(page, 'core.email_verification', 'disabled');

        // Disable the non-admin user's account.
        await navigate(page, `user/${ids.nonadmin}`);
        await expect(page.locator('.g-user-name')).toHaveText('Not Admin');
        await waitForIdlePage(page);
        await page.locator('.g-user-actions-button').click();
        await page.locator('.g-disable-user').click();
        await waitForIdlePage(page);
        await expect(page.locator('#g-alerts-container .alert-success')).toBeVisible();

        await logout(page);
    });

    test('Try to login a disabled user', async ({ page }) => {
        await expect(page.locator('.g-login')).toBeVisible();

        await page.locator('.g-login').click();
        await waitForDialog(page);
        await expect(page.locator('input#g-login')).toBeVisible();
        await waitForFocused(page, '#g-login');

        await page.locator('#g-login').fill('nonadmin');
        await page.locator('#g-password').fill('newpassword');
        await page.locator('#g-login-button').click();

        await expect(page.locator('#g-dialog-container .g-validation-failed-message'))
            .toContainText('disabled');

        await page.locator('#g-dialog-container a[data-dismiss="modal"]').click();
        await expect(page.locator('#g-dialog-container')).toBeHidden();
    });
});
