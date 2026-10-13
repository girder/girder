import { expect, test } from '@playwright/test';

import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/versionSpec.js
 *
 * The original Jasmine spec rendered the front page and asserted that the
 * version element was present exactly once and that its text began with a
 * semantic version (major.minor.patch). It was written to guard against the
 * build injecting a bad/`undefined` version into the page.
 *
 * In the 5.x client the front page is still rendered from frontPage.pug, which
 * only emits the `code.g-version` element `if version`. That value comes from
 * the `version` module, which in turn reads the build-time
 * `import.meta.env.GIRDER_VERSION`. External/release builds set a version, but
 * the plain `npm run build` used by this test suite does not, so in the test
 * environment the version is null and the element is intentionally absent.
 *
 * The assertions below therefore check the original intent (the reported
 * version is never the literal string "undefined") and the conditional
 * rendering behavior: if a version is configured there must be exactly one
 * `.g-version` element containing it, and otherwise the element must not be
 * rendered.
 */

test.describe('Test version reporting', () => {
    setupServer();

    test('check front page version', async ({ page }) => {
        // Wait for the front page body to render, as the original spec did
        // with waitsFor() before running its assertions.
        await expect(page.locator('.g-frontpage-body')).toBeVisible();

        const version = await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            return window.girder.version;
        }) as string | null;

        // The regression the original spec guarded against: the version being
        // present but literally "undefined". It must be a valid version string
        // (as set by the build) or null (no version configured).
        expect(version).not.toBe('undefined');
        expect(version === null || /^\d+\.\d+\.\d+/.test(String(version))).toBe(true);

        const versionElements = page.locator('.g-version');
        if (version === null) {
            // No version was configured at build time, so the front page must
            // not render a version element.
            await expect(versionElements).toHaveCount(0);
        } else {
            // Better checks are possible, but this at least ensures that the
            // version isn't 'undefined'.
            await expect(versionElements).toHaveCount(1);
            const versionText = (await versionElements.textContent())?.trim() ?? '';
            expect(versionText.toLowerCase()).toMatch(/^\d+\.\d+\.\d+/);
            expect(versionText).toContain(String(version));
        }
    });
});
