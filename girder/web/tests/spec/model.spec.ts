import { expect, test, type Route } from '@playwright/test';

import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/modelSpec.js
 *
 * The original spec exercised the base girder Model class with a jasmine spy
 * installed on girder.rest.restRequest. In the Playwright environment the
 * client is served as a bundled ESM application, so internal module bindings
 * cannot be monkey-patched from the page. Instead, requests made to the
 * sample resource are intercepted at the network layer with page.route, and
 * each request's method, URL and parameters are recorded for assertion.
 *
 * Behavioral effects that the original spy could not observe directly are
 * checked by side effects in the page:
 *  - passing "error: null" to restRequest suppresses the default error
 *    handler, which would otherwise trigger a global "g:alert" event;
 *  - model failures trigger "g:error" on the model instance.
 */

interface RecordedRequest {
    method: string;
    url: string;
    params: Record<string, string>;
}

/** Parse an "a=1&b=2" style body or query string into an object. */
const parseParams = (raw: string): Record<string, string> => {
    const params: Record<string, string> = {};
    for (const part of raw.split('&')) {
        if (!part) {
            continue;
        }
        const [key, value = ''] = part.split('=');
        params[decodeURIComponent(key)] = decodeURIComponent(value);
    }
    return params;
};

const SAMPLE_ID = '012345678901234567890123';

test.describe('Test the model class', () => {
    setupServer();

    test('test the base model', async ({ page }) => {
        const requests: RecordedRequest[] = [];
        const state = { error: false };

        /**
         * Intercept all requests to the sample resource, recording each one
         * and either fulfilling it with an empty object or rejecting it with
         * a 500 response, depending on the state.error flag.
         */
        await page.route(/\/api\/v1\/sampleResource/, async (route: Route) => {
            const request = route.request();
            let params: Record<string, string> = {};
            if (request.method() === 'GET' || request.method() === 'DELETE') {
                params = parseParams(new URL(request.url()).search.replace(/^\?/, ''));
            } else {
                params = parseParams(request.postData() ?? '');
            }
            requests.push({
                method: request.method(),
                url: request.url(),
                params,
            });
            if (state.error) {
                await route.fulfill({
                    status: 500,
                    contentType: 'application/json',
                    body: JSON.stringify({ type: 'girder', message: 'mock failure' }),
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: '{}',
                });
            }
        });

        // Listen for global alerts (triggered by the default restRequest error
        // handler whenever "error: null" is not passed) and track model errors.
        await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            window.__modelAlerts = [];
            // @ts-ignore - window.girder is available at runtime
            window.girder.events.on('g:alert', (info: unknown) => {
                // @ts-ignore - window.girder is available at runtime
                window.__modelAlerts.push(info);
            });
        });
        const getAlertCount = async () => await page.evaluate(() => {
            // @ts-ignore - window.girder is available at runtime
            return window.__modelAlerts.length;
        });

        // Create the model class and test name() and increment().
        const base = await page.evaluate((id) => {
            // @ts-ignore - window.girder is available at runtime
            const SampleModel = window.girder.models.Model.extend({
                resourceName: 'sampleResource',
            });
            const model = new SampleModel({});
            // @ts-ignore - window.girder is available at runtime
            window.__model = model;
            // @ts-ignore - window.girder is available at runtime
            window.__modelErrors = 0;
            model.on('g:error', () => {
                // @ts-ignore - window.girder is available at runtime
                window.__modelErrors += 1;
            });

            model.set('name', 'sample');
            const name = model.name();

            const countBefore = model.get('count');
            model.set('count', 0);
            model.increment('count');
            const count1 = model.get('count');
            model.increment('count');
            const count2 = model.get('count');
            model.increment('count', 10);
            const count3 = model.get('count');
            model.increment('count', 0);
            const count4 = model.get('count');

            // save without a resourceName or altUrl should throw
            model.resourceName = null;
            let saveThrows = false;
            try {
                model.save();
            } catch {
                saveThrows = true;
            }
            model.resourceName = 'sampleResource';

            return { id, name, countBefore, count1, count2, count3, count4, saveThrows };
        }, SAMPLE_ID);

        expect(base.name).toBe('sample');
        expect(base.countBefore).toBe(undefined);
        expect(base.count1).toBe(1);
        expect(base.count2).toBe(2);
        expect(base.count3).toBe(12);
        expect(base.count4).toBe(12);
        expect(base.saveThrows).toBe(true);
        expect(requests.length).toBe(0);

        // test save (create)
        await page.evaluate(() => {
            const model = (window as any).__model;
            return new Promise((resolve, reject) => {
                model.save().done(resolve).fail(reject);
            });
        });
        expect(requests.length).toBe(1);
        expect(requests[0].method).toBe('POST');
        expect(requests[0].url).toMatch(/\/api\/v1\/sampleResource$/);
        expect(requests[0].params).toEqual({ count: '12', name: 'sample' });

        // Test save to update
        await page.evaluate((id) => {
            const model = (window as any).__model;
            model.set('_id', id);
            return new Promise((resolve, reject) => {
                model.save().done(resolve).fail(reject);
            });
        }, SAMPLE_ID);
        expect(requests.length).toBe(2);
        expect(requests[1].method).toBe('PUT');
        expect(requests[1].url).toMatch(new RegExp(`/api/v1/sampleResource/${SAMPLE_ID}$`));
        expect(requests[1].params).toEqual({ count: '12', name: 'sample', _id: SAMPLE_ID });

        // A failed save triggers g:error on the model, but since the model
        // passes error: null, the default error handler does not fire.
        state.error = true;
        await page.evaluate(async () => {
            const model = (window as any).__model;
            try {
                await new Promise((resolve, reject) => {
                    model.save().done(resolve).fail(reject);
                });
            } catch {
                // expected failure
            }
        });
        expect(requests.length).toBe(3);
        expect(await getAlertCount()).toBe(0);
        expect(await page.evaluate(() => (window as any).__modelErrors)).toBe(1);
        state.error = false;

        // test fetch: without a resourceName or altUrl it should throw
        requests.length = 0;
        const fetchThrows = await page.evaluate(() => {
            const model = (window as any).__model;
            model.resourceName = null;
            let threw = false;
            try {
                model.fetch();
            } catch {
                threw = true;
            }
            model.resourceName = 'sampleResource';
            return threw;
        });
        expect(fetchThrows).toBe(true);
        expect(requests.length).toBe(0);

        await page.evaluate(async () => {
            const model = (window as any).__model;
            await new Promise((resolve, reject) => {
                model.fetch().done(resolve).fail(reject);
            });
        });
        expect(requests.length).toBe(1);
        expect(requests[0].method).toBe('GET');
        expect(requests[0].url).toMatch(new RegExp(`/api/v1/sampleResource/${SAMPLE_ID}$`));
        expect(requests[0].params).toEqual({});

        await page.evaluate(async () => {
            const model = (window as any).__model;
            await new Promise((resolve, reject) => {
                model.fetch({ extraPath: 'abc' }).done(resolve).fail(reject);
            });
        });
        expect(requests.length).toBe(2);
        expect(requests[1].url).toMatch(new RegExp(`/api/v1/sampleResource/${SAMPLE_ID}/abc$`));

        // fetch with ignoreError: true passes error: null, so a failure does
        // not trigger the default error handler.
        state.error = true;
        await page.evaluate(async () => {
            const model = (window as any).__model;
            try {
                await new Promise((resolve, reject) => {
                    model.fetch({ ignoreError: true }).done(resolve).fail(reject);
                });
            } catch {
                // expected failure
            }
        });
        expect(requests.length).toBe(3);
        expect(requests[2].url).toMatch(new RegExp(`/api/v1/sampleResource/${SAMPLE_ID}$`));
        expect(await getAlertCount()).toBe(0);
        expect(await page.evaluate(() => (window as any).__modelErrors)).toBe(2);
        state.error = false;

        await page.evaluate(async () => {
            const model = (window as any).__model;
            await new Promise((resolve, reject) => {
                model.fetch({ data: { param1: 'value1' } }).done(resolve).fail(reject);
            });
        });
        expect(requests.length).toBe(4);
        expect(requests[3].params).toEqual({ param1: 'value1' });

        // A failing fetch without ignoreError triggers both g:error on the
        // model and the default global error alert.
        state.error = true;
        await page.evaluate(async () => {
            const model = (window as any).__model;
            try {
                await new Promise((resolve, reject) => {
                    model.fetch().done(resolve).fail(reject);
                });
            } catch {
                // expected failure
            }
        });
        state.error = false;
        expect(requests.length).toBe(5);
        expect(await getAlertCount()).toBe(1);
        expect(await page.evaluate(() => (window as any).__modelErrors)).toBe(3);

        // destroy: without a resourceName or altUrl it should throw
        requests.length = 0;
        const destroyThrows = await page.evaluate(() => {
            const model = (window as any).__model;
            model.resourceName = null;
            let threw = false;
            try {
                model.destroy();
            } catch {
                threw = true;
            }
            model.resourceName = 'sampleResource';
            return threw;
        });
        expect(destroyThrows).toBe(true);
        expect(requests.length).toBe(0);

        await page.evaluate(async () => {
            const model = (window as any).__model;
            await new Promise((resolve, reject) => {
                model.destroy().done(resolve).fail(reject);
            });
        });
        expect(requests.length).toBe(1);
        expect(requests[0].method).toBe('DELETE');
        expect(requests[0].url).toMatch(new RegExp(`/api/v1/sampleResource/${SAMPLE_ID}$`));
        expect(requests[0].params).toEqual({});

        await page.evaluate(async () => {
            const model = (window as any).__model;
            await new Promise((resolve, reject) => {
                model.destroy({ progress: true }).done(resolve).fail(reject);
            });
        });
        expect(requests.length).toBe(2);
        expect(requests[1].params).toEqual({ progress: 'true' });

        // destroy with throwError: false does not pass error: null, so a
        // failure triggers the default global error alert.
        state.error = true;
        await page.evaluate(async () => {
            const model = (window as any).__model;
            try {
                await new Promise((resolve, reject) => {
                    model.destroy({ throwError: false }).done(resolve).fail(reject);
                });
            } catch {
                // expected failure
            }
        });
        expect(requests.length).toBe(3);
        expect(requests[2].params).toEqual({});
        expect(await getAlertCount()).toBe(2);
        expect(await page.evaluate(() => (window as any).__modelErrors)).toBe(4);

        // A plain destroy passes error: null, so a failure does not alert.
        await page.evaluate(async () => {
            const model = (window as any).__model;
            try {
                await new Promise((resolve, reject) => {
                    model.destroy().done(resolve).fail(reject);
                });
            } catch {
                // expected failure
            }
        });
        state.error = false;
        expect(requests.length).toBe(4);
        expect(await getAlertCount()).toBe(2);
        expect(await page.evaluate(() => (window as any).__modelErrors)).toBe(5);

        // getAccessLevel
        const accessLevels = await page.evaluate(() => {
            const model = (window as any).__model;
            const before = model.getAccessLevel();
            model.set('_accessLevel', 'abc');
            return { before, after: model.getAccessLevel() };
        });
        expect(accessLevels.before).toBe(undefined);
        expect(accessLevels.after).toBe('abc');

        // test downloadUrl
        const downloadUrls = await page.evaluate(() => {
            const model = (window as any).__model;
            return {
                plain: model.downloadUrl(),
                withParams: model.downloadUrl({ foo: 'bar' }),
                apiRoot: window.girder.rest.getApiRoot(),
            };
        });
        expect(downloadUrls.plain).toBe(`${downloadUrls.apiRoot}/sampleResource/${SAMPLE_ID}/download`);
        expect(downloadUrls.withParams).toBe(`${downloadUrls.apiRoot}/sampleResource/${SAMPLE_ID}/download?foo=bar`);

        // test download: model.download() navigates the page to the download
        // URL. The navigation is fulfilled by the route handler above and the
        // resulting request is recorded. This must come last, since the
        // navigation replaces the application page and tears down its state.
        await page.evaluate(() => {
            (window as any).__model.download();
        }).catch(() => {
            // The navigation may tear down the execution context before the
            // evaluate response is delivered; that is expected.
        });
        await expect.poll(() => requests.filter((r) => /\/api\/v1\/sampleResource\/.+\/download$/.test(r.url)).length)
            .toBe(1);
        const downloadRequest = requests.find((r) => /\/api\/v1\/sampleResource\/.+\/download$/.test(r.url));
        expect(downloadRequest?.method).toBe('GET');
    });
});
