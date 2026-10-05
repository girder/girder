import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, waitForIdlePage } from '../util';

async function asyncRestRequest(page: Page, opts: any) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            window.girder.rest.restRequest(opts).done((resp: any) => {
                resolve(resp);
            }).fail((resp: any) => {
                reject(resp);
            });
        });
    }, opts);
}

async function selectedNames(page: Page) {
    return page.evaluate(() => {
        const girder = (window as any).girder;
        const $ = girder.$;
        const names: string[] = [];
        $('.g-selected .g-item-list-link').each((index: number, el: any) => {
            names.push($(el).clone().children().remove().end().text());
        });
        return names;
    });
}

test.describe('Slicer CLI web item selector regex selection', () => {
    setupServer();

    test('browser hierarchy paginated selection', async ({ page }) => {
        await createUser(page, 'admin');
        await waitForIdlePage(page);

        // Seed a folder hierarchy with many items through REST.
        const me = await asyncRestRequest(page, { url: '/user/me' }) as any;
        const folder = await asyncRestRequest(page, {
            url: '/folder',
            method: 'POST',
            data: { name: 'top level folder', parentType: 'user', parentId: me._id },
        }) as any;
        await asyncRestRequest(page, {
            url: '/folder',
            method: 'POST',
            data: { name: 'subfolder', parentType: 'folder', parentId: folder._id },
        });
        const item = await asyncRestRequest(page, {
            url: '/item',
            method: 'POST',
            data: { name: 'an item', folderId: folder._id },
        }) as any;
        for (let i = 0; i < 20; i += 1) {
            await asyncRestRequest(page, {
                url: '/item',
                method: 'POST',
                data: { name: `item#: ${i}`, folderId: folder._id },
            });
        }
        await waitForIdlePage(page);

        // Instantiate the multi-file selector directly against the seeded folder.
        await page.evaluate(async ({ folderId, itemId }) => {
            const girder = (window as any).girder;
            const slicer = girder.plugins.slicer_cli_web;
            const folderModel = new girder.models.FolderModel({ _id: folderId });
            await new Promise((resolve, reject) => {
                folderModel.once('g:fetched', resolve).once('g:error', reject).fetch();
            });
            const itemModel = new girder.models.ItemModel({ _id: itemId });
            const dialogEl = girder.$('<div/>').appendTo('body');
            const selector = new slicer.views.ItemSelectorWidget({
                parentView: { registerChildView: () => undefined },
                el: dialogEl.get(0),
                rootPath: folderModel,
                root: folderModel,
                defaultSelectedResource: itemModel,
                selectItem: true,
                showItems: true,
                model: new slicer.models.WidgetModel({
                    type: 'multi',
                    title: 'Title',
                    id: 'item-widget',
                }),
            });
            selector.once('g:saved', () => {
                selector.$el.modal('hide');
            });
            (window as any).__itemSelector = selector;
            selector.render();
        }, { folderId: folder._id, itemId: item._id });

        await expect(page.locator('.g-item-list-entry')).toHaveCount(21);

        const input = page.locator('#g-input-element');

        await input.fill('[0-9][1-3]');
        await expect(page.locator('.g-selected .g-item-list-link')).not.toHaveCount(0);
        let names = await selectedNames(page);
        expect(names).not.toContain('item#: 10');
        expect(names).toContain('item#: 11');
        expect(names).toContain('item#: 12');
        expect(names).toContain('item#: 13');
        expect(names).not.toContain('item#: 14');

        await input.fill(' [4-7]$');
        await expect(page.locator('.g-selected .g-item-list-link')).not.toHaveCount(0);
        names = await selectedNames(page);
        expect(names).toContain('item#: 4');
        expect(names).toContain('item#: 5');
        expect(names).toContain('item#: 6');
        expect(names).toContain('item#: 7');
        expect(names).not.toContain('item#: 14');
        expect(names).not.toContain('item#: 17');

        await input.fill('');
        await expect(page.locator('.g-selected .g-item-list-link')).toHaveCount(21);

        await input.fill('\\');
        await expect(page.locator('.g-selected .g-item-list-link')).toHaveCount(0);
        await expect(page.locator('.g-validation-failed-message:visible')).toHaveCount(1);

        await page.evaluate(() => (window as any).__itemSelector.$('.g-submit-button').click());
        await expect(page.locator('.g-validation-failed-message:visible')).toHaveCount(1);

        // Resetting the selector re-highlights every item.
        await page.evaluate(() => {
            const selector = (window as any).__itemSelector;
            selector.$('#g-input-element').val('');
            selector._selectModel();
            selector._hierarchyView.itemListView.trigger('g:changed');
        });
        await expect(page.locator('.g-selected .g-item-list-link')).toHaveCount(21);

        await input.fill('[5]$');
        await expect(page.locator('.g-selected .g-item-list-link')).not.toHaveCount(0);
        names = await selectedNames(page);
        expect(names).toContain('item#: 5');
        expect(names).toContain('item#: 15');

        await page.evaluate(() => (window as any).__itemSelector.$('.g-submit-button').click());
        await expect.poll(() => page.evaluate(() => {
            const model = (window as any).__itemSelector.model;
            const value = model.get('value');
            return value ? value.get('name') : null;
        })).toBe('[5]$');

        const state = await page.evaluate(() => {
            const model = (window as any).__itemSelector.model;
            return {
                path: model.get('path'),
                folderName: model.get('folderName'),
            };
        });
        expect(state.path.filter(Boolean)).toEqual(['top level folder']);
        expect(state.folderName).toBe('top level folder');
    });
});
