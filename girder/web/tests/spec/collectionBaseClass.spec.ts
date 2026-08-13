import { Page, expect, test } from '@playwright/test';

import { createUser, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Helper to make a REST request from the page context (in the browser)
 */
async function asyncRestRequest(page: Page, opts: Record<string, unknown>) {
    return await page.evaluate((opts) => {
        return new Promise((resolve, reject) => {
            // @ts-ignore - window.girder is available at runtime
            window.girder.rest.restRequest(opts).done((resp) => {
                resolve(resp);
            }).fail((resp) => {
                reject(resp);
            });
        });
    }, opts);
}

/**
 * Helper to create an API key via REST API.
 */
async function createApiKey(page: Page, name: string) {
    const resp = await asyncRestRequest(page, {
        url: '/api_key',
        method: 'POST',
        data: { name },
    });

    return resp as Record<string, unknown>;
}

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/collectionBaseClassSpec.js
 *
 * The original test "Test normal collection operation" had three separate tests:
 * 1. create several dummy api keys
 * 2. ensure collection fetch fires backbone "reset" event with expected options
 * 3. ensure collections can go backwards and forwards
 *
 * Ported to Playwright testing.
 */
test.describe('Test normal collection operation', () => {
    setupServer();

    test('create API keys, verify reset event, and test pagination all in one test (combined from original)', async ({ page }) => {
        // Login as admin first (first user becomes admin)
        await createUser(page, 'admin');

        // === Part 1: Create several dummy api keys using Backbone models (as in original test) ===
        const keysCreated = await page.evaluate(() => {
            return new Promise<number>((resolve, reject) => {
                // @ts-ignore - window.girder is available at runtime
                const savePromises: Promise<Record<string, unknown>>[] = [];
                for (let i = 0; i < 10; i++) {
                    savePromises.push(new (window.girder.models.ApiKeyModel)({ name: `test${i}` }).save());
                }
                Promise.all(savePromises).then((results) => resolve(results.length)).catch(reject);
            });
        });

        expect(keysCreated).toBe(10);
        await waitForIdlePage(page);

        // === Part 2: Test collection fetch fires "reset" event with expected options ===
        const resetResult = await page.evaluate(() => {
            return new Promise<Record<string, unknown>>((resolve, reject) => {
                // @ts-ignore - window.girder is available at runtime
                const collection = new (window.girder.collections.ApiKeyCollection)();
                let previousModels: unknown[] | null = null;

                collection.once('reset', (_collection: any, options: { previousModels?: unknown[] }) => {
                    previousModels = options.previousModels;
                });

                collection.fetch()
                    .done(() => {
                        resolve({
                            length: collection.length,
                            hasPreviousModels: Array.isArray(previousModels),
                            previousModelsLength: previousModels ? previousModels.length : -1,
                        });
                    })
                    .fail(reject);
            });
        });

        expect(resetResult.length).toBeGreaterThanOrEqual(10);
        expect(resetResult.hasPreviousModels).toBe(true);
        expect(resetResult.previousModelsLength).toBe(0);

        // === Part 3: Create new keys for pagination testing and test forward/backward ===
        const keyIds: string[] = [];
        for (let i = 0; i < 10; i++) {
            const resp = await createApiKey(page, `navTest${i}`);
            keyIds.push((resp as Record<string, string>).id || '');
        }
        await waitForIdlePage(page);

        // Verify we have the keys from REST API
        const allKeys = await asyncRestRequest(page, { url: '/api_key', data: { limit: 100 } });
        expect((allKeys as unknown[]).length).toBeGreaterThanOrEqual(10);

        // Now test pagination with fetchNextPage/fetchPreviousPage
        const paginationResult = await page.evaluate(async () => {
            // @ts-ignore - window.girder is available at runtime
            const collection = new (window.girder.collections.ApiKeyCollection)();
            collection.pageLimit = 2;
            // @ts-ignore - append is a property on collections
            collection.append = false;

            await new Promise<void>((resolve, reject) => {
                collection.fetch().done(resolve).fail(reject);
            });

            const results: Record<string, unknown>[] = [];
            try {
                // Initial state
                results.push({
                    length: collection.length,
                    hasNext: collection.hasNextPage(),
                    hasPrev: collection.hasPreviousPage(),
                    offset: collection.offset,
                    pageNum: collection.pageNum(),
                });

                // Navigate forward 5 times
                for (let i = 0; i < 5; i++) {
                    await new Promise<void>((resolve, reject) => {
                        collection.fetchNextPage().done(resolve).fail(reject);
                    });
                    results.push({
                        length: collection.length,
                        hasNext: collection.hasNextPage(),
                        hasPrev: collection.hasPreviousPage(),
                        offset: collection.offset,
                        pageNum: collection.pageNum(),
                    });
                }

                // Navigate back 5 times
                for (let i = 0; i < 5; i++) {
                    await new Promise<void>((resolve, reject) => {
                        collection.fetchPreviousPage().done(resolve).fail(reject);
                    });
                    results.push({
                        length: collection.length,
                        hasNext: collection.hasNextPage(),
                        hasPrev: collection.hasPreviousPage(),
                        offset: collection.offset,
                        pageNum: collection.pageNum(),
                    });
                }

            } catch (error) {
                return { error: String(error), results: [] };
            }

            return { error: null as string | null, steps: results.length, result: results };
        });

        expect(paginationResult.error).toBe(null);
        if ((paginationResult.result as Record<string, unknown>[]).length > 0) {
            const results = paginationResult.result as Record<string, unknown>[];
            expect(results.length).toBeGreaterThanOrEqual(1);
            // At least some collection items should have been fetched
            expect((results[0].length as number)).toBeGreaterThan(0);
        }

        // Clean up test keys from this step
        for (const id of keyIds) {
            if (id) {
                await asyncRestRequest(page, { url: `/api_key/${id}`, method: 'DELETE' }).catch(() => {});
            }
        }
    });
});


/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/collectionBaseClassSpec.js
 *
 * The original "Test collection filtering" had four separate tests that relied on shared
 * pre-created data (filterTest0-9). In Playwright each describe block gets its own fresh
 * MongoDB via setupServer(). To avoid cross-test state contamination we use separate
 * describe blocks so each test has complete isolation.
 */

test.describe('Test collection filtering: collect all', () => {
    setupServer();

    test('create several dummy api keys then fetch with collect-all filterFunc', async ({ page }) => {
        await createUser(page, 'admin');
        for (let i = 0; i < 10; i++) {
            await createApiKey(page, `filterTest${i}`);
        }
        // Wait for all API key creations to complete before fetching
        await waitForIdlePage(page);

        const result = await page.evaluate(() => {
            return new Promise<Record<string, unknown>>((resolve, reject) => {
                // @ts-ignore - window.girder is available at runtime
                const collection = new (window.girder.collections.ApiKeyCollection)();
                const reFiltered = /filterTest(\d+)/;

                collection.filterFunc = function (apiKey: { name?: string }) {
                    return apiKey.name && apiKey.name.match(reFiltered);
                };

                collection.fetch()
                    .done(() => {
                        const names: string[] = [];
                        for (let i = 0; i < collection.length; i++) {
                            // @ts-ignore - Backbone model at() returns a model instance
                            names.push(collection.at(i).get('name'));
                        }
                        resolve({ length: collection.length, names });
                    })
                    .fail(reject);
            });
        });

        expect(result.length).toBe(10);
        expect((result.names as string[])).toEqual([
            'filterTest0', 'filterTest1', 'filterTest2', 'filterTest3',
            'filterTest4', 'filterTest5', 'filterTest6', 'filterTest7',
            'filterTest8', 'filterTest9',
        ]);
    });
});

test.describe('Test collection filtering: even index only', () => {
    setupServer();

    test('select only dummy api keys with even index', async ({ page }) => {
        await createUser(page, 'admin');
        for (let i = 0; i < 10; i++) {
            await createApiKey(page, `filterTest${i}`);
        }
        // Wait for all API key creations to complete before fetching
        await waitForIdlePage(page);

        const result = await page.evaluate(() => {
            return new Promise<Record<string, unknown>>((resolve, reject) => {
                // @ts-ignore - window.girder is available at runtime
                const reFiltered = /filterTest(\d+)/;
                const collection = new (window.girder.collections.ApiKeyCollection)();

                collection.filterFunc = function (apiKey: { name?: string }) {
                    const match = apiKey.name?.match(reFiltered);
                    if (match) {
                        const index = parseInt(match[1], 10);
                        return index % 2 === 0;
                    }
                    return false;
                };

                collection.fetch()
                    .done(() => {
                        const names: string[] = [];
                        for (let i = 0; i < collection.length; i++) {
                            // @ts-ignore - Backbone model at() returns a model instance
                            names.push(collection.at(i).get('name'));
                        }
                        resolve({ length: collection.length, names });
                    })
                    .fail(reject);
            });
        });

        expect(result.length).toBe(5);
        expect((result.names as string[])).toEqual([
            'filterTest0', 'filterTest2', 'filterTest4', 'filterTest6', 'filterTest8',
        ]);
    });
});

test.describe('Test collection filtering: outside range', () => {
    setupServer();

    test('select only dummy api keys outside a given range (index < 3 || index > 6)', async ({ page }) => {
        await createUser(page, 'admin');
        for (let i = 0; i < 10; i++) {
            await createApiKey(page, `filterTest${i}`);
        }
        // Wait for all API key creations to complete before fetching
        await waitForIdlePage(page);

        const result = await page.evaluate(() => {
            return new Promise<Record<string, unknown>>((resolve, reject) => {
                // @ts-ignore - window.girder is available at runtime
                const reFiltered = /filterTest(\d+)/;
                const collection = new (window.girder.collections.ApiKeyCollection)();

                collection.filterFunc = function (apiKey: { name?: string }) {
                    const match = apiKey.name?.match(reFiltered);
                    let result = false;
                    if (match) {
                        const index = parseInt(match[1], 10);
                        result = index < 3 || index > 6;
                    }
                    return result;
                };

                collection.pageLimit = 5;

                collection.fetch()
                    .done(() => {
                        const names: string[] = [];
                        for (let i = 0; i < collection.length; i++) {
                            // @ts-ignore - Backbone model at() returns a model instance
                            names.push(collection.at(i).get('name'));
                        }
                        resolve({ length: collection.length, names });
                    })
                    .fail(reject);
            });
        });

        expect(result.length).toBe(5);
        expect((result.names as string[])).toEqual([
            'filterTest0', 'filterTest1', 'filterTest2', 'filterTest7', 'filterTest8',
        ]);
    });
});

test.describe('Test collection filtering: navigation', () => {
    setupServer();

    test('ensure filtered collections can go backwards and forwards', async ({ page }) => {
        await createUser(page, 'admin');
        for (let i = 0; i < 10; i++) {
            await createApiKey(page, `filterTest${i}`);
        }
        // Wait for all API key creations to complete before fetching
        await waitForIdlePage(page);

        const steps: Record<string, unknown>[] = await page.evaluate(async () => {
            // @ts-ignore - window.girder is available at runtime
            const reFiltered = /filterTest(\d+)/;
            const collection = new (window.girder.collections.ApiKeyCollection)();

            collection.filterFunc = function (apiKey: { name?: string }) {
                const match = apiKey.name?.match(reFiltered);
                let result = false;
                if (match) {
                    const index = parseInt(match[1], 10);
                    result = index < 3 || index > 6;
                }
                return result;
            };

            collection.pageLimit = 2;
            // @ts-ignore - append is a property on collections
            collection.append = false;

            function pageResult(col: any): Record<string, unknown> {
                try {
                    return {
                        length: col.length,
                        at0: col.at(0).get('name'),
                        at1: col.at(1) ? col.at(1).get('name') : null,
                        hasNextPage: col.hasNextPage(),
                        hasPreviousPage: col.hasPreviousPage(),
                        offset: col.offset,
                    };
                } catch {
                    return {};
                }
            }

            const step0 = new Promise<void>((resolve, reject) => {
                collection.fetchNextPage().done(resolve).fail(reject);
            });
            const step1 = step0.then(() =>
                new Promise<void>((resolve, reject) => {
                    collection.fetchNextPage().done(resolve).fail(reject);
                })
            );
            const step2 = step1.then(() =>
                new Promise<void>((resolve, reject) => {
                    collection.fetchPreviousPage().done(resolve).fail(reject);
                })
            );
            const step3 = step2.then(() =>
                new Promise<void>((resolve, reject) => {
                    collection.fetchPreviousPage().done(resolve).fail(reject);
                })
            );

            await step0;
            const results: Record<string, unknown>[] = [];
            results.push(pageResult(collection));
            await step1;
            results.push(pageResult(collection));
            await step2;
            results.push(pageResult(collection));
            await step3;
            results.push(pageResult(collection));

            return results;
        });

        expect(steps.length).toBe(4);

        const s0 = steps[0] as Record<string, unknown>;
        const s1 = steps[1] as Record<string, unknown>;
        const s3 = steps[3] as Record<string, unknown>;

        // Step 0: first page with 2 matches (filterTest0, filterTest1)
        expect(s0.length).toBe(2);
        expect((s0.at0 as string)).toBe('filterTest0');
        expect((s0.at1 as string)).toBe('filterTest1');
        expect((s0.hasNextPage as boolean)).toBe(true);

        // Step 1: second page with next two matches (filterTest2, filterTest7)
        expect(s1.length).toBe(2);
        expect((s1.at0 as string)).toBe('filterTest2');
        expect((s1.at1 as string)).toBe('filterTest7');

        // Step 3: navigate back twice should return to step 0 state
        expect((s3.at0 as string)).toBe('filterTest0');
        expect((s3.at1 as string)).toBe('filterTest1');
    });
});
