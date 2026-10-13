import { Page, expect, test } from '@playwright/test';

import { createUser, login, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/emptyLayoutSpec.js
 *
 * Tests that the empty and default app layouts toggle the visibility of the
 * app header, global nav, and footer as expected, and that the body container
 * gets the appropriate layout class.
 */

const HEADER = '#g-app-header-container';
const GLOBAL_NAV = '#g-global-nav-container';
const FOOTER = '#g-app-footer-container';
const BODY = '#g-app-body-container';

/**
 * Register the two custom routes used by the original spec, exactly as the
 * original test did, using the app exposed at window.girder.
 */
async function registerLayoutRoutes(page: Page) {
    await page.evaluate(() => {
        // @ts-ignore - window.girder is available at runtime
        const g = window.girder;
        g.router.route('collections/emptylayout', 'collectionsEmptyLayout', (params: Record<string, unknown>) => {
            g.events.trigger(
                'g:navigateTo',
                g.views.body.CollectionsView,
                params || {},
                { layout: g.constants.Layout.EMPTY },
            );
        });
        g.router.route('collections/defaultlayout', 'collectionsDefaultLayout', (params: Record<string, unknown>) => {
            g.events.trigger(
                'g:navigateTo',
                g.views.body.CollectionsView,
                params || {},
                { layout: g.constants.Layout.DEFAULT },
            );
        });
    });
}

/** Equivalent of girderTest.testRoute: navigate to a fragment with trigger. */
async function navigate(page: Page, route: string) {
    await page.evaluate((r) => {
        // @ts-ignore - window.girder is available at runtime
        window.girder.router.navigate(r, { trigger: true });
    }, route);
}

async function expectEmptyLayout(page: Page) {
    // ensure that all components we expect hidden are hidden
    await expect(page.locator(HEADER)).toBeHidden();
    await expect(page.locator(GLOBAL_NAV)).toBeHidden();
    await expect(page.locator(FOOTER)).toBeHidden();
    // ensure the empty layout is present
    await expect(page.locator(BODY)).toHaveClass(/g-empty-layout/);
    // and the default layout is absent
    await expect(page.locator(BODY)).not.toHaveClass(/g-default-layout/);
    // test that body elements remain visible
    await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
}

async function expectDefaultLayout(page: Page) {
    // ensure that all components we expect revealed are visible
    await expect(page.locator(HEADER)).toBeVisible();
    await expect(page.locator(GLOBAL_NAV)).toBeVisible();
    await expect(page.locator(FOOTER)).toBeVisible();
    // ensure the default layout is present
    await expect(page.locator(BODY)).toHaveClass(/g-default-layout/);
    // and the empty layout is absent
    await expect(page.locator(BODY)).not.toHaveClass(/g-empty-layout/);
    // test that body elements remain visible
    await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
}

test.describe('Test empty and default layouts', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('register a user (first is admin)', async ({ page }) => {
        await createUser(
            page,
            'admin',
            'admin@girder.test',
            'Admin',
            'Admin',
            'adminpassword!',
        );
    });

    test('go to collections empty layout page', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');

        // wait for app header container to appear so we can know it will disappear
        await expect(page.locator(HEADER)).toBeVisible({ timeout: 10000 });

        await registerLayoutRoutes(page);

        await navigate(page, 'collections/emptylayout');

        // be sure that app header is gone, and collection list has finished loading
        await expect(page.locator(HEADER)).toBeHidden();
        await expect(page.locator('.g-collection-list-header:visible')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('.g-collection-create-button:visible')).toBeVisible({ timeout: 10000 });

        await expectEmptyLayout(page);
    });

    test('go to standard collections page, test that not passing a layout will revert to default', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');
        await registerLayoutRoutes(page);

        // route back to the standard collections view, this should
        // revert to the default layout
        await navigate(page, 'collections');

        // be sure that app header is back, and collection list has finished loading
        await expect(page.locator(HEADER)).toBeVisible({ timeout: 10000 });
        await expect(page.locator('.g-collection-list-header:visible')).toBeVisible({ timeout: 10000 });

        await expectDefaultLayout(page);
    });

    test('go to collections empty layout page, then specify a default layout', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');

        // wait for app header container to appear so we can know it will disappear
        await expect(page.locator(HEADER)).toBeVisible({ timeout: 10000 });

        await registerLayoutRoutes(page);

        // go to emptylayout, be sure that app header is gone, and collection list has finished loading
        await navigate(page, 'collections/emptylayout');
        await expect(page.locator(HEADER)).toBeHidden();
        await expect(page.locator('.g-collection-list-header:visible')).toBeVisible({ timeout: 10000 });

        await expectEmptyLayout(page);

        // this should revert to the default layout
        await navigate(page, 'collections/defaultlayout');
        // be sure that app header is back, and collection list has finished loading
        await expect(page.locator(HEADER)).toBeVisible({ timeout: 10000 });
        await expect(page.locator('.g-collection-list-header:visible')).toBeVisible({ timeout: 10000 });

        await expectDefaultLayout(page);

        await waitForIdlePage(page);
    });
});
