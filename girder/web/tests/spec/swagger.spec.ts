import { execFileSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

import { expect, test } from '@playwright/test';

import { setupServer } from '../server';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/swaggerSpec.js
 *
 * In the 5.x client the API documentation is no longer a client-side Backbone
 * route; it is a standalone server-rendered swagger-ui page served at
 * `/api/v1` (see `girder/api/api_docs.mako`).  This spec therefore navigates
 * directly to that URL rather than exercising the single page app.
 *
 * The original spec used swagger-ui 2.x DOM selectors.  The current page uses
 * swagger-ui 5.20.1, whose markup differs:
 *   - a tag is still `#operations-tag-<tag>`, and its label is an `<a>` with a
 *     nested `<span>`;
 *   - an operation is still `#operations-<tag>-<operationId>` (for this route
 *     that is `#operations-system-system_getVersion_version`), but it must be
 *     expanded by clicking its `.opblock-summary` before the execute button
 *     exists;
 *   - the execute control is `button.execute`.
 */

test.describe('Test the swagger pages', () => {
    setupServer();

    test('Test swagger', async ({ page }) => {
        await page.goto(new URL('/api/v1', page.url()).toString());

        // Wait for the swagger docs to appear and check the system tag.
        const systemTag = page.locator('#operations-tag-system');
        await expect(systemTag).toBeVisible();
        await expect(page.locator('#operations-tag-system a span')).toHaveText('system');

        // Expand the system tag so its operations become visible.
        await page.locator('#operations-tag-system a').click();
        const versionOperation = page.locator('#operations-system-system_getVersion_version');
        await expect(versionOperation).toBeVisible();

        // Expand the getVersion operation so its execute button becomes visible.
        await versionOperation.locator('.opblock-summary').click();
        const executeButton = versionOperation.locator('button.execute');
        await expect(executeButton).toBeVisible();

        // Execute the request and wait for the server's version information.
        await executeButton.click();
        await expect(versionOperation.locator('.highlight-code code')).toContainText('release');
    });

    test('The swagger description is valid', async ({ page }) => {
        // Fetch the OpenAPI/Swagger description that the page above is built
        // from and validate it with Redocly's linter, mirroring:
        //   curl -s <server>/api/v1/describe | jq > /tmp/swagger.json &&
        //   npx -y @redocly/cli lint /tmp/swagger.json \
        //     --max-problems 10000 --skip-rule no-ambiguous-paths
        const describeResponse = await page.request.get(
            new URL('/api/v1/describe', page.url()).toString(),
        );
        expect(describeResponse.ok()).toBe(true);

        const describePath = path.join(
            fs.mkdtempSync(path.join(os.tmpdir(), 'girder-swagger-')),
            'swagger.json',
        );
        fs.writeFileSync(describePath, await describeResponse.text());

        // Redocly writes its report to stderr, so the validation result is
        // expressed through the process exit code: execFileSync throws when
        // the linter exits non-zero (i.e. the description is invalid).
        execFileSync(
            path.join(__dirname, '..', '..', 'node_modules', '.bin', 'redocly'),
            [
                'lint', describePath,
                '--max-problems', '10000',
                '--skip-rule', 'no-ambiguous-paths',
            ],
            { stdio: 'pipe' },
        );
    });
});
