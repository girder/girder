import { Page, expect, test } from '@playwright/test';

import { createUser, login, waitForDialog, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/widgetsSpec.js
 *
 * The original spec covered two widgets that were not exercised elsewhere:
 *   1. the task progress widget (TaskProgressWidget / ProgressListView), driven
 *      by progress notifications, and
 *   2. the folder info widget's asynchronous "details" fetch.
 *
 * Adaptations from the Jasmine original:
 *
 * - The original drove progress through the `webclienttest/progress` REST
 *   endpoint, which used a `ProgressContext` to publish `progress`
 *   notifications over the user's event stream (a websocket). The Playwright
 *   test harness does not register that test-only endpoint, so the equivalent
 *   progress notifications are emitted directly on the client's event stream.
 *   This exercises the same code path in the client (ProgressListView listens
 *   for `g:event.progress` and renders a TaskProgressWidget per notification),
 *   which is what the original spec was actually asserting against.
 * - The original relied on the registration from the preceding `it` leaving a
 *   user logged in. Playwright gives every test a fresh browser context, so
 *   the tests that need a user log in explicitly.
 */

/** The shape of the `data` member of a progress notification. */
interface ProgressData {
    title: string;
    total: number;
    current: number;
    state: 'active' | 'success' | 'error';
    message: string;
    resource: { _id: string | null };
    resourceName: string | null;
}

/** The shape of the payload published on the event stream for progress. */
interface ProgressPayload {
    _id: string;
    type: 'progress';
    data: ProgressData;
    startTime: number;
    updatedTime?: number;
    estimatedTotalTime?: number;
}

let progressId = 0;

const makeProgress = (
    state: ProgressData['state'],
    message: string,
    options: Partial<ProgressData> & Partial<Pick<ProgressPayload, 'updatedTime' | 'estimatedTotalTime'>> = {},
): ProgressPayload => {
    progressId += 1;
    const { updatedTime, estimatedTotalTime, ...data } = options;
    return {
        _id: `test-progress-${progressId}`,
        type: 'progress',
        data: {
            title: 'Progress Test',
            total: 0,
            current: 0,
            state,
            message,
            resource: { _id: null },
            resourceName: null,
            ...data,
        },
        startTime: 0,
        ...(updatedTime === undefined ? {} : { updatedTime }),
        ...(estimatedTotalTime === undefined ? {} : { estimatedTotalTime }),
    };
};

/** Publish a progress notification on the client's event stream. */
const emitProgress = async (page: Page, payload: ProgressPayload) => {
    await page.evaluate((progress) => {
        // @ts-ignore - window.girder is available at runtime
        window.girder.utilities.eventStream.trigger('g:event.progress', progress);
    }, payload);
};

test.describe('Test task progress widget', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('register a user', async ({ page }) => {
        await createUser(
            page,
            'admin',
            'admin@girder.test',
            'Admin',
            'Admin',
            'adminpassword!',
        );
    });

    test('test task progress widget', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');

        // No progress notifications are present initially, so the progress
        // area is hidden.
        await expect(page.locator('#g-app-progress-container')).toBeHidden();

        // A successful progress notification renders the title and its final
        // "Done" message.
        await emitProgress(page, makeProgress('success', 'Done'));
        await expect(page.locator('.g-task-progress-title').last()).toHaveText('Progress Test');
        await expect(page.locator('.g-task-progress-message').last()).toHaveText('Done');

        // An error notification renders the corresponding error message.
        await emitProgress(page, makeProgress('error', 'Error: Progress error test.'));
        await expect(page.locator('.g-task-progress-title').last()).toHaveText('Progress Test');
        await expect(page.locator('.g-task-progress-message').last()).toHaveText(
            'Error: Progress error test.',
        );

        // Progress notifications are delivered as `g:event.progress` events and
        // must not produce `g:error` events.
        await page.evaluate(() => {
            const w = window as any;
            w.__progressEvents = 0;
            w.__errorEvents = 0;
            w.__onProgress = () => {
                w.__progressEvents += 1;
            };
            w.__onError = () => {
                w.__errorEvents += 1;
            };
            w.girder.utilities.eventStream.on('g:event.progress', w.__onProgress);
            w.girder.utilities.eventStream.on('g:error', w.__onError);
        });
        await emitProgress(page, makeProgress('success', 'Done'));
        await expect
            .poll(() => page.evaluate(() => (window as any).__progressEvents))
            .toBeGreaterThan(0);
        expect(await page.evaluate(() => (window as any).__errorEvents)).toBe(0);

        // A progress notification associated with a resource links to it.
        await emitProgress(
            page,
            makeProgress('success', 'Done', {
                resource: { _id: 'some_folder_id' },
                resourceName: 'folder',
            }),
        );
        await expect(page.locator('.g-task-progress-title').last().locator('a')).toHaveAttribute(
            'href',
            '#folder/some_folder_id',
        );

        // A long-running task shows a percentage and an estimated time left.
        await emitProgress(
            page,
            makeProgress('active', 'Progress Message', {
                total: 100,
                current: 5,
                updatedTime: 100,
                estimatedTotalTime: 200,
            }),
        );
        await expect(page.locator('.g-task-progress-message').last()).toHaveText('Progress Message');
        expect(await page.locator('.g-progress-widget-container').count()).toBeGreaterThan(0);
        await expect(page.locator('.progress-status .progress-percent').last()).toHaveText('5.0%');
        await expect(page.locator('.progress-status .progress-left').last()).toHaveText(/left$/);

        // Successful notifications fade out after a few seconds; at least one of
        // the completed notifications should disappear on its own.
        await expect
            .poll(() => page.locator('.g-progress-widget-container').count())
            .toBeLessThan(4);

        // Closing the event stream clears all outstanding progress.
        await page.evaluate(() => {
            (window as any).girder.utilities.eventStream.close();
        });
        await expect(page.locator('.g-progress-widget-container')).toHaveCount(0);

        // Clean up the test changes, restoring the event stream and removing
        // the listeners added above.
        await page.evaluate(() => {
            const w = window as any;
            w.girder.utilities.eventStream.off('g:event.progress', w.__onProgress);
            w.girder.utilities.eventStream.off('g:error', w.__onError);
            w.girder.utilities.eventStream.open();
        });
        await expect(page.locator('.g-user-dropdown-link')).toBeVisible();
    });
});

test.describe('Test folder info widget async fetch', () => {
    setupServer();
    test.describe.configure({ mode: 'serial' });

    test('register a user', async ({ page }) => {
        await createUser(
            page,
            'admin',
            'admin@girder.test',
            'Admin',
            'Admin',
            'adminpassword!',
        );
    });

    test("fetch the current user's folders", async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');

        const folderCount = await page.evaluate(async () => {
            // @ts-ignore - window.girder is available at runtime
            const g = window.girder;
            if (g.auth.getCurrentUser() === null) {
                throw new Error('expected a current user');
            }
            const folders = new g.collections.FolderCollection();
            await new Promise<void>((resolve, reject) => {
                folders
                    .fetch({
                        parentType: 'user',
                        parentId: g.auth.getCurrentUser().id,
                    })
                    .done(() => resolve())
                    .fail((err: unknown) => reject(new Error(`folder fetch failed: ${String(err)}`)));
            });
            return folders.models.length;
        });

        expect(folderCount).toBeGreaterThan(0);
    });

    test('show a folder info widget for one of the folders', async ({ page }) => {
        await login(page, 'admin', 'adminpassword!');

        const folderId = await page.evaluate(async () => {
            // @ts-ignore - window.girder is available at runtime
            const g = window.girder;
            if (g.auth.getCurrentUser() === null) {
                throw new Error('expected a current user');
            }
            const folders = new g.collections.FolderCollection();
            await new Promise<void>((resolve, reject) => {
                folders
                    .fetch({
                        parentType: 'user',
                        parentId: g.auth.getCurrentUser().id,
                    })
                    .done(() => resolve())
                    .fail((err: unknown) => reject(new Error(`folder fetch failed: ${String(err)}`)));
            });

            const model = folders.models[0];
            model.set('description', 'hello world');

            // The widget fetches the folder's details and then renders itself
            // into the dialog container.
            new g.views.widgets.FolderInfoWidget({
                el: document.getElementById('g-dialog-container'),
                model,
                parentView: null,
            });

            return model.id;
        });

        await waitForDialog(page);
        await expect(page.locator('.modal-body .g-folder-description')).toContainText('hello world');

        await expect(page.locator('.g-folder-info-line[property="nItems"]')).toHaveText(
            'Contains 0 items totaling 0 B',
        );
        await expect(page.locator('.g-folder-info-line[property="nFolders"]')).toHaveText(
            'Contains 0 subfolders',
        );
        await expect(
            page.locator(`.g-folder-info-line[property="id"]:has-text("${folderId}")`),
        ).toHaveCount(1);

        await page.locator('#g-dialog-container .btn-default').click();
        await waitForIdlePage(page);
        await expect(page.locator('#g-dialog-container')).toBeHidden();
    });
});
