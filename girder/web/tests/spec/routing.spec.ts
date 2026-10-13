import { Page, expect, test } from '@playwright/test';

import { createUser, login, waitForDialog, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/routingSpec.js
 *
 * Tests that navigating to the various application routes loads the expected
 * view and/or dialog.  The original spec relied on a database fixture
 * (routingSpec.yml) that seeded an admin user with a "Link File" item, a "Test
 * Collection" with a "Private" folder, and a public group.  The Playwright
 * infrastructure does not expose fixture loading, so the same data is created
 * through the REST API before the route tests run.  The original spec used a
 * single sequential Jasmine describe sharing an `ids` object; this port keeps
 * that sequence in a serial Playwright describe so each test gets a fresh page
 * while the server and database are shared.
 */

const ADMIN = {
    login: 'admin',
    email: 'admin@girder.test',
    firstName: 'Admin',
    lastName: 'Admin',
    password: 'adminpassword!',
};

/** Make a REST request from within the page context and await its result. */
async function api(page: Page, opts: Record<string, unknown>) {
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

/** Return the id of the currently logged in user. */
async function currentUserId(page: Page): Promise<string> {
    return await page.evaluate(() => {
        // @ts-ignore - window.girder is available at runtime
        return window.girder.auth.getCurrentUser().get('_id');
    });
}

/** Create a folder via the REST API. */
async function createFolder(page: Page, parentType: string, parentId: string, name: string): Promise<string> {
    const folder = await api(page, {
        url: '/folder',
        method: 'POST',
        data: { parentType, parentId, name },
    }) as { _id: string };
    return folder._id;
}

/** Create an item via the REST API. */
async function createItem(page: Page, folderId: string, name: string): Promise<string> {
    const item = await api(page, {
        url: '/item',
        method: 'POST',
        data: { folderId, name },
    }) as { _id: string };
    return item._id;
}

/** Create a link file on an item via the REST API. */
async function createLinkFile(page: Page, itemId: string, name: string, linkUrl: string): Promise<string> {
    const file = await api(page, {
        url: '/file',
        method: 'POST',
        data: { parentType: 'item', parentId: itemId, name, linkUrl },
    }) as { _id: string };
    return file._id;
}

/** Create a group via the REST API. */
async function createGroup(page: Page, name: string, description: string, isPublic: boolean): Promise<string> {
    const group = await api(page, {
        url: '/group',
        method: 'POST',
        data: { name, description, public: isPublic },
    }) as { _id: string };
    return group._id;
}

/** Navigate within the single page app (equivalent of girderTest.testRoute). */
async function navigate(page: Page, route: string) {
    await page.evaluate((r) => {
        // @ts-ignore - window.girder is available at runtime
        window.girder.router.navigate(r, { trigger: true });
    }, route);
}

/**
 * Navigate to a route and, if it is not a dialog route, wait for the app to
 * finish loading the new view and any outstanding REST requests.
 */
async function testRoute(page: Page, route: string, hasDialog: boolean) {
    await navigate(page, route);
    if (hasDialog) {
        await waitForDialog(page);
    } else {
        await waitForIdlePage(page);
    }
}

test.describe('Test routing paths', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    const ids: Record<string, string> = {};

    test('register the admin user', async ({ page }) => {
        await createUser(
            page,
            ADMIN.login,
            ADMIN.email,
            ADMIN.firstName,
            ADMIN.lastName,
            ADMIN.password,
        );
    });

    test('create a public group', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        const groupId = await createGroup(page, 'Public Group', 'public group', true);
        ids.group = groupId;
        await waitForIdlePage(page);
    });

    test('collect ids for tests', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);
        await waitForIdlePage(page);

        ids.admin = await currentUserId(page);

        // The admin user's private top level folder.
        const userFolders = await api(page, {
            url: '/folder',
            method: 'GET',
            data: { parentType: 'user', parentId: ids.admin },
        }) as { _id: string, name: string }[];
        const privateFolder = userFolders.find((f) => f.name === 'Private');
        if (!privateFolder) {
            throw new Error('Could not find the admin user Private folder');
        }
        ids.userFolder = privateFolder._id;

        // The "Link File" item and its linked file.
        const item = await createItem(page, ids.userFolder, 'Link File');
        ids.item = item;
        ids.file = await createLinkFile(page, ids.item, 'Link File', 'https://girder.test/routingSpec.yml');

        // The "Test Collection" and its private folder.
        const collection = await api(page, {
            url: '/collection',
            method: 'POST',
            data: { name: 'Test Collection', description: 'Collection Description', public: true },
        }) as { _id: string };
        ids.collection = collection._id;
        ids.collectionFolder = await createFolder(page, 'collection', ids.collection, 'Private');

        // The first assetstore.
        const assetstores = await api(page, {
            url: '/assetstore',
            method: 'GET',
        }) as { _id: string }[];
        ids.assetstore = assetstores[0]._id;

        await waitForIdlePage(page);
    });

    test('test routes without being logged in', async ({ page }) => {
        await waitForIdlePage(page);

        await testRoute(page, '', false);
        await expect(page.locator('a.g-login-link').first()).toBeVisible();

        await testRoute(page, `useraccount/${ids.admin}/info`, false);
        await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('');

        await testRoute(page, `useraccount/${ids.admin}/password`, false);
        await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('');

        await testRoute(page, '?dialog=login', true);
        await expect(page.locator('label[for=g-login]')).toHaveText('Login or email');

        await testRoute(page, '?dialog=register', true);
        await expect(page.locator('input#g-password2')).toHaveCount(1);

        await testRoute(page, '?dialog=resetpassword', true);
        await expect(page.locator('.modal-title')).toHaveText('Forgotten password');

        /* Navigate to a non-dialog so we can log in. */
        await testRoute(page, 'collections', false);
        await expect(page.locator('.g-collection-title').first()).toHaveText('Test Collection');
    });

    test('test routes while logged in', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        await testRoute(page, '', false);
        await expect(page.locator('a.g-my-folders-link').first()).toContainText('personal data space');

        await testRoute(page, `useraccount/${ids.admin}/info`, false);
        await expect(page.locator('input#g-email')).toHaveValue(ADMIN.email);

        await testRoute(page, `useraccount/${ids.admin}/password`, false);
        await expect(page.locator('input#g-password-old:visible')).toHaveCount(1);

        await testRoute(page, '?dialog=login', false);
        await expect(page.locator('a.g-my-folders-link').first()).toContainText('personal data space');

        await testRoute(page, '?dialog=register', false);
        await expect(page.locator('a.g-my-folders-link').first()).toContainText('personal data space');

        await testRoute(page, '?dialog=resetpassword', false);
        await expect(page.locator('a.g-my-folders-link').first()).toContainText('personal data space');
    });

    test('test collection routes', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        await testRoute(page, 'collections', false);
        await expect(page.locator('.g-collection-title').first()).toHaveText('Test Collection');

        await testRoute(page, 'collections?dialog=create', true);
        await expect(page.locator('input#g-name')).toHaveAttribute('placeholder', 'Enter collection name');

        const collPath = `collection/${ids.collection}`;
        await testRoute(page, collPath, false);
        await expect(page.locator('.g-collection-actions-menu')).toHaveCount(1);

        await testRoute(page, `${collPath}?dialog=edit`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit collection');

        await testRoute(page, `${collPath}?dialog=access`, true);
        await expect(page.locator('.g-dialog-subtitle')).toHaveText('Test Collection');

        await testRoute(page, `${collPath}?dialog=foldercreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create folder');

        const collFolderPath = `${collPath}/folder/${ids.userFolder}`;
        await testRoute(page, collFolderPath, false);
        await expect(page.locator('.g-collection-actions-menu')).toHaveCount(1);
        await expect(page.locator('.g-folder-access-button')).toHaveCount(1);

        await testRoute(page, `${collFolderPath}?dialog=edit`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit collection');

        await testRoute(page, `${collFolderPath}?dialog=access`, true);
        await expect(page.locator('.g-dialog-subtitle')).toHaveText('Test Collection');

        await testRoute(page, `${collFolderPath}?dialog=foldercreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create folder');

        await testRoute(page, `${collFolderPath}?dialog=folderedit`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit folder');
        await expect(page.locator('input#g-name')).toHaveValue('Private');

        await testRoute(page, `${collFolderPath}?dialog=folderaccess`, true);
        await expect(page.locator('.g-dialog-subtitle')).toHaveText('Private');

        await testRoute(page, `${collFolderPath}?dialog=itemcreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create item');

        await testRoute(page, `${collFolderPath}?dialog=upload`, true);
        await expect(page.locator('.modal-title')).toHaveText('Upload files');
    });

    test('test user routes', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        await testRoute(page, 'users', false);
        await expect(page.locator('.g-user-link').first()).toHaveText('Admin Admin');

        const userPath = `user/${ids.admin}`;
        await testRoute(page, userPath, false);
        await expect(page.locator('.g-user-actions-button')).toHaveCount(1);

        await testRoute(page, `${userPath}?dialog=foldercreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create folder');

        const userFolderPath = `${userPath}/folder/${ids.userFolder}`;
        await testRoute(page, userFolderPath, false);
        await expect(page.locator('.g-user-actions-button')).toHaveCount(1);
        await expect(page.locator('.g-folder-access-button')).toHaveCount(1);

        await testRoute(page, `${userFolderPath}?dialog=foldercreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create folder');

        await testRoute(page, `${userFolderPath}?dialog=folderedit`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit folder');
        await expect(page.locator('input#g-name')).toHaveValue('Private');

        await testRoute(page, `${userFolderPath}?dialog=folderaccess`, true);
        await expect(page.locator('.g-dialog-subtitle')).toHaveText('Private');

        await testRoute(page, `${userFolderPath}?dialog=itemcreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create item');

        await testRoute(page, `${userFolderPath}?dialog=upload`, true);
        await expect(page.locator('.modal-title')).toHaveText('Upload files');

        const folderPath = `folder/${ids.userFolder}`;
        await testRoute(page, folderPath, false);
        await expect(page.locator('.g-user-actions-button')).toHaveCount(0);
        await expect(page.locator('.g-folder-access-button')).toHaveCount(1);

        await testRoute(page, `${folderPath}?dialog=foldercreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create folder');

        await testRoute(page, `${folderPath}?dialog=folderedit`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit folder');
        await expect(page.locator('input#g-name')).toHaveValue('Private');

        await testRoute(page, `${folderPath}?dialog=folderaccess`, true);
        await expect(page.locator('.g-dialog-subtitle')).toHaveText('Private');

        await testRoute(page, `${folderPath}?dialog=itemcreate`, true);
        await expect(page.locator('.modal-title')).toHaveText('Create item');

        await testRoute(page, `${folderPath}?dialog=upload`, true);
        await expect(page.locator('.modal-title')).toHaveText('Upload files');
    });

    test('test group routes', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        await testRoute(page, 'groups', false);
        await expect(page.locator('.g-group-link').first()).toHaveText('Public Group');

        await testRoute(page, 'groups?dialog=create', true);
        await expect(page.locator('input#g-name')).toHaveAttribute('placeholder', 'Enter group name');

        const groupPath = `group/${ids.group}`;
        const hiddenEmptyLists = () => page.evaluate(() => {
            // @ts-ignore - jQuery is available at runtime
            return window.girder.$('.g-member-list-empty:hidden').length;
        });

        await testRoute(page, `${groupPath}/roles`, false);
        await expect(page.locator('.g-member-name:visible')).toHaveCount(1);
        await expect(page.locator('#g-group-tab-roles .g-member-list-empty:visible')).toHaveCount(2);
        expect(await hiddenEmptyLists()).toBe(2);

        await testRoute(page, `${groupPath}/pending`, false);
        await expect(page.locator('.g-group-requests-container:visible')).toHaveCount(1);
        await expect(page.locator('#g-group-tab-pending .g-member-list-empty:visible')).toHaveCount(2);
        expect(await hiddenEmptyLists()).toBe(2);

        await testRoute(page, `${groupPath}?dialog=edit`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit group');
    });

    test('test item routes', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        const itemPath = `item/${ids.item}`;
        await testRoute(page, itemPath, false);
        await expect(page.locator('.g-item-header .g-item-name')).toHaveText('Link File');

        await testRoute(page, `${itemPath}?dialog=itemedit`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit item');

        await testRoute(page, `${itemPath}?dialog=fileedit&dialogid=${ids.file}`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit file');

        await testRoute(page, `${itemPath}?dialog=upload&dialogid=${ids.file}`, true);
        await expect(page.locator('.modal-title')).toHaveText('Replace file contents');

        await testRoute(page, `${itemPath}?dialog=fileedit&dialogid=${ids.file}`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit file');
    });

    test('test admin routes', async ({ page }) => {
        await login(page, ADMIN.login, ADMIN.password);

        await testRoute(page, 'admin', false);
        await expect(page.locator('.g-server-config')).toHaveCount(1);

        await testRoute(page, 'settings', false);
        await expect(page.locator('input#g-core-cookie-lifetime')).toHaveCount(1);

        await testRoute(page, 'plugins', false);
        await expect(page.locator('.g-body-title')).toHaveText(/^Plugins/);

        await testRoute(page, 'assetstores', false);
        await expect(page.locator('.g-assetstore-container')).toHaveCount(1);

        await testRoute(page, `assetstores?dialog=assetstoreedit&dialogid=${ids.assetstore}`, true);
        await expect(page.locator('.modal-title')).toHaveText('Edit assetstore');
    });
});

test.describe('Test internal javascript functions', () => {
    setupServer();

    test('check parseQueryString', async ({ page }) => {
        await createUser(page, 'admin', ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);

        const results = await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            const g = window.girder;
            const testVals = [
                { plain: 'strings' },
                { altchar: 'a~`!@#$%^&*()_+{}|[]\\:";\'<>?,./' },
            ];
            return testVals.map((val) => {
                const encode = g.$.param(val);
                return g.$.param(g.misc.parseQueryString(encode)) === encode;
            });
        });
        expect(results).toEqual([true, true]);
    });
});

test.describe('Test disabling the router at runtime', () => {
    setupServer();

    test('router should be enabled by default and disabled at runtime', async ({ page }) => {
        await createUser(page, 'admin', ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);

        const result = await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            const g = window.girder;
            const router = g.Backbone.Router.prototype;
            const calls: unknown[] = [];
            const original = router.navigate;
            router.navigate = function (this: unknown, ...args: unknown[]) {
                calls.push(args);
                return original.apply(this, args as never[]);
            };

            // The router should be enabled by default.
            const enabledByDefault = g.router.enabled();
            g.router.navigate('collections', { trigger: true });
            const callsWhenEnabled = calls.length;

            // Disabling the router should make navigate() a no-op.
            g.router.enabled(false);
            g.router.navigate('users', { trigger: true });
            const callsWhenDisabled = calls.length;

            router.navigate = original;
            return { enabledByDefault, callsWhenEnabled, callsWhenDisabled };
        });

        expect(result.enabledByDefault).toBe(true);
        expect(result.callsWhenEnabled).toBeGreaterThan(0);
        expect(result.callsWhenDisabled).toBe(result.callsWhenEnabled);
    });
});
