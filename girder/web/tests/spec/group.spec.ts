import { Page, expect, test } from '@playwright/test';

import { createUser, login, logout, waitForDialog, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/groupSpec.js
 * Tests for "Test group actions".
 */

/**
 * Make a REST request from within the page context and await its result.
 */
async function asyncRestRequest(page: Page, opts: Record<string, unknown>) {
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

/**
 * Update a system setting, as the currently logged in (admin) user.
 */
async function setSetting(page: Page, key: string, value: string) {
    await asyncRestRequest(page, {
        url: 'system/setting',
        method: 'PUT',
        data: { key, value },
    });
}

/**
 * Navigate to the groups list page.
 */
async function gotoGroupsPage(page: Page) {
    await page.locator('a.g-nav-link[g-target="groups"]').click();
    await expect(page.locator('.g-group-search-form .g-search-field')).toBeVisible();
}

/**
 * Create a group and wait for its page to load. Assumes the user is on the
 * groups page and logged in.
 */
async function createGroup(page: Page, name: string, description: string, isPublic: boolean) {
    await expect(page.locator('.g-group-create-button')).toBeVisible();
    await page.locator('.g-group-create-button').click();
    await waitForDialog(page);
    await expect(page.locator('#g-name')).toBeVisible();
    if (isPublic) {
        await page.locator('#g-access-public').click();
        await expect(page.locator('.g-public-container .radio.g-selected')).toContainText('Public');
    }
    await page.locator('#g-name').fill(name);
    await page.locator('#g-description').fill(description);
    await page.locator('.g-save-group').click();
    await waitForIdlePage(page);
    await expect(page.locator('.g-group-name')).toHaveText(name);
    await expect(page.locator('.g-group-description')).toHaveText(description);
}

/**
 * Open a named group from the groups list page.
 */
async function openGroup(page: Page, name: string) {
    const entry = page.locator('.g-group-list-entry', { hasText: name });
    await expect(entry.locator('.g-group-link')).toBeVisible();
    await entry.locator('.g-group-link').click();
    await expect(page.locator('.g-group-name')).toHaveText(name);
}

/**
 * Wait for the pubGroup page to be in the state established when the admin
 * force-adds user1, user2, and user3: one member, one moderator, two admins.
 */
async function expectGroupLoaded(page: Page) {
    await expect(page.locator('.g-group-name')).toHaveText('pubGroup');
    await expect(page.locator('.g-group-members > li')).toHaveCount(1);
    await expect(page.locator('.g-group-mods > li')).toHaveCount(1);
    await expect(page.locator('.g-group-admins > li')).toHaveCount(2);
}

/**
 * Click the confirm button in a confirmation dialog and wait for it to close.
 */
async function confirmDialog(page: Page) {
    await expect(page.locator('#g-confirm-button')).toBeVisible();
    await page.locator('#g-confirm-button').click();
    await waitForIdlePage(page);
}

/**
 * Search for a name on the members search panel, and invite or add the first
 * found user as a member, moderator, or admin.
 *
 * @param name: name to search for.
 * @param level: 'member', 'moderator', or 'admin'.
 * @param action: 'invite' or 'add'.
 * @param check: if true or false, assert if the action exists, then cancel the
 *               dialog.
 */
async function invite(
    page: Page,
    name: string,
    level: 'member' | 'moderator' | 'admin',
    action: 'invite' | 'add',
    check?: boolean,
) {
    // Search for the named user in the user search box
    const searchField = page.locator('.g-group-invite-container input.g-search-field');
    await expect(searchField).toBeVisible();
    await searchField.fill(name);

    const results = page.locator('.g-group-invite-container .g-search-results');
    await expect(results).toHaveClass(/open/);

    const resultItems = page.locator('.g-group-invite-container li.g-search-result');
    await expect(resultItems).toHaveCount(2); // 1 + '...' element
    const userLinks = page.locator('.g-group-invite-container a[data-resource-type="user"]');
    await expect(userLinks).toHaveCount(1);
    await userLinks.first().click();

    await waitForDialog(page);
    await expect(page.locator('.g-invite-as-member.btn')).toHaveCount(1);

    if (level !== 'member') {
        const sel = level === 'moderator' ? 'moderator' : 'administrator';
        const panelTitle = page
            .locator('#g-invite-role-container .panel-title', { hasText: `Invite as ${sel}` })
            .locator('a');
        await panelTitle.click();
    }

    const actionButton = page.locator(`.g-${action}-as-${level}`);
    if (check === true) {
        await expect(actionButton).toHaveCount(1);
        await page.locator('#g-dialog-container .modal-footer a').click();
    } else if (check === false) {
        await expect(actionButton).toHaveCount(0);
        await expect(page.locator(`.g-invite-as-${level}`)).toHaveCount(1);
        await page.locator('#g-dialog-container .modal-footer a').click();
    } else {
        await actionButton.click();
    }
    await waitForIdlePage(page);
}

/**
 * Test if a combination of user and add-to-group policy has the expected
 * ability to directly add members.
 *
 * @param policy: a dictionary of user, setting, and mayAdd. user is the name
 *                of the user to test, setting is the value for the policy, and
 *                mayAdd is either null (no invitation dialog), or a boolean
 *                (true if direct adds are allowed).
 * @param curUser: the current logged in user.
 * @param curSetting: the current policy setting.
 */
async function testDirectAdd(
    page: Page,
    policy: { user: number | string; setting: string; mayAdd: boolean | null },
    curUser: string,
    curSetting: string,
) {
    if (curSetting !== policy.setting) {
        if (curUser !== 'admin') {
            await logout(page);
            await login(page, 'admin', 'adminpassword!');
            curUser = 'admin';
        }
        await setSetting(page, 'core.add_to_group_policy', policy.setting);
        /* Navigate away and back to make the group reload unless we are going
         * to change users */
        if (curUser === policy.user) {
            await gotoGroupsPage(page);
            await openGroup(page, 'pubGroup');
            await expectGroupLoaded(page);
        }
    }
    if (curUser !== policy.user) {
        await logout(page);
        if (policy.user === 'admin') {
            await login(page, 'admin', 'adminpassword!');
        } else {
            await login(page, `user${policy.user}`, 'password!');
        }
        curUser = policy.user as string;
        // go back to the groups page since we've logged out
        await gotoGroupsPage(page);
        await openGroup(page, 'pubGroup');
        await expectGroupLoaded(page);
    }

    /* If the invite search field exists or we think it should,
     * test that the add button exists as we expect */
    if (policy.mayAdd === null) {
        await expect(page.locator('.g-group-invite-container input.g-search-field')).toHaveCount(0);
    } else {
        await invite(page, 'admin', 'member', 'add', policy.mayAdd);
    }

    return { curUser, curSetting: policy.setting };
}

test.describe('Test group actions', () => {
    setupServer();

    test('register a user (first is admin) and check that groups page is blank', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');

        await gotoGroupsPage(page);
        await expect(page.locator('.g-group-list-entry')).toHaveCount(0);
    });

    test('create a private group and check anonymous loading prompts login', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await createGroup(page, 'privGroup', 'private group', false);

        // Capture the route to the private group.
        const url = page.url();
        const match = url.match(/group\/([a-f0-9]+)/);
        expect(match).not.toBeNull();
        const privateGroupFragment = `group/${match![1]}/roles`;

        // Log out, then load the private group anonymously.
        await logout(page);
        await page.evaluate((fragment) => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.router.navigate(fragment, { trigger: true });
        }, privateGroupFragment);

        // The login dialog should be prompted.
        await waitForDialog(page);
        await expect(page.locator('input#g-login')).toBeVisible();
        await page.locator('#g-dialog-container .modal-header .close').click();
        await waitForIdlePage(page);

        // Return to the front page and log back in.
        await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.router.navigate('', { trigger: true });
        });
        await login(page, 'admin', 'adminpassword!');
    });

    test('create a public group and open edit dialog to check url state', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await createGroup(page, 'pubGroup', 'public group', true);

        // Open the group actions menu.
        const actionsButton = page.locator('.g-group-actions-button');
        await expect(actionsButton).toBeVisible();
        await actionsButton.click();

        const editAction = page.locator('.g-edit-group');
        await expect(editAction).toBeVisible();
        await editAction.click();

        // The url state should change and the edit dialog should appear.
        await expect
            .poll(() => page.evaluate(() => window.location.hash))
            .toContain('/roles?dialog=edit');
        await waitForDialog(page);

        const cancelButton = page.locator('#g-dialog-container a.btn-default');
        await expect(cancelButton).toHaveText('Cancel');
        await cancelButton.click();
        await waitForIdlePage(page);
    });

    test('have the admin remove and then force add themself to the group', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await openGroup(page, 'pubGroup');

        await page.locator('.g-group-admin-remove').click();
        await confirmDialog(page);

        // Admin user removes themself from the group.
        await expect(page.locator('ul.g-group-members > li')).toHaveCount(0);

        await invite(page, 'admin', 'member', 'add');

        await expect(page.locator('ul.g-group-members > li')).toHaveCount(1);
    });

    test('check that logging out of a group and groups list redirects to the front page', async ({ page }) => {
        // Logout from a group page.
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await openGroup(page, 'privGroup');
        await logout(page);
        await expect(page.locator('.g-frontpage-title')).toBeVisible();

        // Logout from the groups list page.
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await logout(page);
        await expect(page.locator('.g-frontpage-title')).toBeVisible();
    });

    test('check groups page visibility for admin and anonymous users', async ({ page }) => {
        // Admin sees both groups.
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await expect(page.locator('.g-group-list-entry')).toHaveCount(2);
        const adminText = (await page.locator('.g-group-list-entry').allInnerTexts()).join(' ');
        expect(adminText).toContain('privGroup');
        expect(adminText).toContain('pubGroup');
        expect(adminText).toContain('private group');
        expect(adminText).toContain('public group');

        // Anonymous users see only the public group.
        await logout(page);
        await gotoGroupsPage(page);
        await expect(page.locator('.g-group-list-entry')).toHaveCount(1);
        const anonText = await page.locator('.g-group-list-entry').innerText();
        expect(anonText).toContain('pubGroup');
        expect(anonText).toContain('public group');
        await page.locator('.g-group-link').first().click();
        await expect(page.locator('.g-group-name')).toHaveText('pubGroup');
    });

    test('check promotion and demotion', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await openGroup(page, 'pubGroup');

        // The admin is the only member; there are no mods or admins.
        await expect(page.locator('.g-group-mods .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-admins .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-members-body')).toHaveCount(1);
        await expect(page.locator('.g-group-members .g-member-name')).toHaveCount(1);

        // Promote to moderator.
        await page.locator('.g-group-members .g-group-member-controls .dropdown .g-group-member-promote').click();
        const promoteModerator = page.locator('.g-group-members .g-group-member-controls .g-promote-moderator');
        await expect(promoteModerator).toBeVisible();
        await promoteModerator.click();
        await expect(page.locator('.g-group-members .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods')).toHaveCount(1);
        await expect(page.locator('.g-group-mod-promote')).toHaveCount(1);

        // Promote to admin.
        await page.locator('.g-group-mod-promote').click();
        await expect(page.locator('.g-group-members .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-admins')).toHaveCount(1);
        await expect(page.locator('.g-group-admin-demote')).toHaveCount(1);

        // Demote admin to moderator.
        await page.locator('.g-group-admin-demote').click();
        const demoteModerator = page.locator('.g-group-admins .g-demote-moderator');
        await expect(demoteModerator).toBeVisible();
        await demoteModerator.click();
        await confirmDialog(page);
        await expect(page.locator('.g-group-members .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-admins .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods')).toHaveCount(1);
        await expect(page.locator('.g-group-mod-promote')).toHaveCount(1);

        // Demote moderator to plain member.
        await page.locator('.g-group-mod-demote').click();
        await confirmDialog(page);
        await expect(page.locator('.g-group-admins .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-members .g-member-name')).toHaveCount(1);

        // Promote directly to admin.
        await page.locator('.g-group-members .g-group-member-controls .dropdown .g-group-member-promote').click();
        const promoteAdmin = page.locator('.g-group-members .g-group-member-controls .g-promote-admin');
        await expect(promoteAdmin).toBeVisible();
        await promoteAdmin.click();
        await expect(page.locator('.g-group-members .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-admins')).toHaveCount(1);
        await expect(page.locator('.g-group-admin-demote')).toHaveCount(1);

        // Demote admin directly to plain member.
        await page.locator('.g-group-admin-demote').click();
        const demoteMember = page.locator('.g-group-admins .g-demote-member');
        await expect(demoteMember).toBeVisible();
        await demoteMember.click();
        await confirmDialog(page);
        await expect(page.locator('.g-group-admins .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-members .g-member-name')).toHaveCount(1);
    });

    test('check member addition and removal', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await openGroup(page, 'pubGroup');

        await page.locator('.g-group-member-remove').click();
        await confirmDialog(page);

        await invite(page, 'admin', 'member', 'invite');
        await invite(page, 'admin', 'moderator', 'invite');
        await invite(page, 'admin', 'admin', 'invite');
        await invite(page, 'admin', 'moderator', 'add');
        await expect(page.locator('.g-group-members .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-admins .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods')).toHaveCount(1);
        await expect(page.locator('.g-group-mod-promote')).toHaveCount(1);

        await page.locator('.g-group-mod-remove').click();
        await confirmDialog(page);

        await invite(page, 'admin', 'admin', 'add');
        await expect(page.locator('.g-group-members .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-admins')).toHaveCount(1);
        await expect(page.locator('.g-group-admin-demote')).toHaveCount(1);

        await page.locator('.g-group-admin-remove').click();
        await confirmDialog(page);

        await invite(page, 'admin', 'admin', 'add');
    });

    test('check ability to directly add users to groups', async ({ page }) => {
        const policyTest: { user: number | string; setting: string; mayAdd: boolean | null }[] = [
            { setting: 'never', user: 1, mayAdd: false },
            { setting: 'nomod', user: 1, mayAdd: false },
            { setting: 'yesadmin', user: 1, mayAdd: true },
            { setting: 'yesadmin', user: 2, mayAdd: false },
            { setting: 'yesadmin', user: 3, mayAdd: null },
            { setting: 'yesmod', user: 2, mayAdd: true },
            { setting: 'never', user: 'admin', mayAdd: true },
            { setting: 'nomod', user: 'admin', mayAdd: true },
        ];

        // Add a bunch of users to facilitate testing.
        for (let i = 1; i <= 3; i += 1) {
            if (i > 1) {
                await logout(page);
            }
            await createUser(page, `user${i}`, `user${i}@girder.test`, `User${i}`, 'User', 'password!');
        }

        // Use the admin user to force-add certain users to the group.
        await logout(page);
        await login(page, 'admin', 'adminpassword!');
        await gotoGroupsPage(page);
        await openGroup(page, 'pubGroup');
        await expect(page.locator('.g-group-name')).toHaveText('pubGroup');
        await expect(page.locator('.g-group-members .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-mods .g-member-list-empty')).toHaveCount(1);
        await expect(page.locator('.g-group-admins')).toHaveCount(1);
        await invite(page, 'user1', 'admin', 'add');
        await invite(page, 'user2', 'moderator', 'add');
        await invite(page, 'user3', 'member', 'add');

        let curUser = 'admin';
        let curSetting = 'never';
        for (let i = 0; i < policyTest.length; i += 1) {
            const policy = policyTest[i];
            ({ curUser, curSetting } = await testDirectAdd(page, policy, curUser, curSetting));
        }

        /* Open and save the group to test that the add-to-group control is
         * shown */
        const actionsButton = page.locator('.g-group-actions-button');
        await expect(actionsButton).toBeVisible();
        await actionsButton.click();

        const editAction = page.locator('.g-edit-group');
        await expect(editAction).toBeVisible();
        await editAction.click();
        await waitForDialog(page);
        await expect(page.locator('#g-add-to-group')).toHaveCount(1);
        await page.locator('.g-save-group').click();
        await waitForIdlePage(page);
    });
});
