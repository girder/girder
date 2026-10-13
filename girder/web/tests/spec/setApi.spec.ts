import { expect, test } from '@playwright/test';

import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/setApiSpec.js
 *
 * Tests the default value of the REST api root and that setApiRoot() mutates
 * it. The original spec asserted against the host-stripped api root
 * (`getApiRoot().slice(getApiRoot().indexOf('/', 7))`), because the 3.x test
 * harness configured an absolute api root including scheme and host. In the
 * 5.x client the api root is a relative path (`/api/v1`), so the default is
 * asserted directly instead.
 */

test.describe('Test setApiRoot() function', () => {
    setupServer();

    test('check for default values and mutation', async ({ page }) => {
        // Wait for the front page to render, as the original spec did.
        await expect(page.locator('.g-frontpage-body')).toBeVisible();

        const result = await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            const g = window.girder;

            // Test the default value.
            const defaultApiRoot = g.rest.getApiRoot();

            // Test mutation.
            const apiRootVal = '/foo/bar/v2';
            g.rest.setApiRoot(apiRootVal);
            return { defaultApiRoot, mutatedApiRoot: g.rest.getApiRoot() };
        });

        expect(result.defaultApiRoot.endsWith('/api/v1')).toBe(true);
        expect(result.mutatedApiRoot).toBe('/foo/bar/v2');
    });
});
