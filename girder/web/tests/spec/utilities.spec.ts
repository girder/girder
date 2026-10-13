import { Page, expect, test } from '@playwright/test';

import { createUser, login } from '../util';
import { setupServer } from '../server';

/**
 * Ported from 3.x-maintenance: girder/web_client/test/spec/utilitiesSpec.js
 *
 * The original spec exercised two unrelated utilities:
 *
 *  1. The EventStream utility (girder.utilities.eventStream), which opens a
 *     websocket once a user logs in, emits `g:eventStream.start`,
 *     `g:eventStream.stop` and `g:eventStream.close`, and reacts to the
 *     document `visibilitychange` event by stopping or starting itself.
 *  2. showDownload(), which walks a view's `parentView` chain and returns the
 *     value of the root view's `showDownload()` method (defaulting to true).
 *
 * The original Jasmine spec relied on shared state between its sequential
 * `it` blocks (a single eventStream instance that was left started/stopped by
 * earlier tests).  Playwright gives every test a fresh page and browser
 * context, so each EventStream test re-establishes the state it needs by
 * logging the user in.  The user itself is registered once, by the first test
 * in the serial describe, and the shared server/database exposes it to the
 * following tests.
 *
 * Between 3.x and 5.x the EventStream was reworked from an EventSource (SSE)
 * transport to a WebSocket transport, with the message parsing, error handler,
 * and "since" timestamp tracking changed.  The original spec predates that
 * rework and only covered the transport-independent lifecycle (start / stop /
 * close events and the visibilitychange behavior).  The tests after the
 * original four are new: they pin down the WebSocket-specific behavior that
 * the ported spec does not cover.
 */

/**
 * Install event counters for the EventStream and replace its visibility
 * handler with one that stops or starts the stream according to
 * `window.__eventStreamTest.mode`.
 *
 * This must run before the user logs in, because `eventStream.open()` registers
 * the (replaced) handler as the document `visibilitychange` listener.  It
 * mirrors the original spec, which used a Jasmine spy to trigger
 * `_stop()`/`_start()` on `visibilitychange` because `document.visibilityState`
 * cannot be mocked.
 */
async function installEventStreamProbe(page: Page) {
    await page.evaluate(() => {
        // @ts-ignore - window.girder is available at runtime
        const eventStream = window.girder.utilities.eventStream;
        // @ts-ignore - test-only global
        window.__eventStreamTest = { start: 0, stop: 0, close: 0, mode: null };

        eventStream.on('g:eventStream.start', () => {
            // @ts-ignore - test-only global
            window.__eventStreamTest.start += 1;
        });
        eventStream.on('g:eventStream.stop', () => {
            // @ts-ignore - test-only global
            window.__eventStreamTest.stop += 1;
        });
        eventStream.on('g:eventStream.close', () => {
            // @ts-ignore - test-only global
            window.__eventStreamTest.close += 1;
        });

        eventStream._onVisibilityStateChange = function () {
            // @ts-ignore - test-only global
            if (window.__eventStreamTest.mode === 'stop') {
                eventStream._stop();
            // @ts-ignore - test-only global
            } else if (window.__eventStreamTest.mode === 'start') {
                eventStream._start();
            }
        };
    });
}

/** Return a snapshot of the EventStream counters. */
async function eventStreamCounts(page: Page) {
    return await page.evaluate(() => {
        // @ts-ignore - test-only global
        return { ...window.__eventStreamTest };
    }) as { start: number; stop: number; close: number; mode: string | null };
}

/** Dispatch the document `visibilitychange` event. */
async function dispatchVisibilityChange(page: Page) {
    await page.evaluate(() => {
        document.dispatchEvent(new CustomEvent('visibilitychange'));
    });
}

/** Set the mode used by the replaced visibility handler. */
async function setVisibilityMode(page: Page, mode: 'stop' | 'start') {
    await page.evaluate((m) => {
        // @ts-ignore - test-only global
        window.__eventStreamTest.mode = m;
    }, mode);
}

/**
 * Replace `window.WebSocket` with a recording fake before the user logs in.
 *
 * The 5.x EventStream constructs a WebSocket in `_start()`.  Using a fake
 * keeps the tests deterministic (no dependence on a live notification socket)
 * and lets them inspect the constructed URL, simulate inbound messages and
 * errors, and observe `close()`.  The recorded state lives on
 * `window.__fakeWebSockets`.
 */
async function installFakeWebSocket(page: Page) {
    await page.evaluate(() => {
        // @ts-ignore - test-only global
        window.__fakeWebSockets = { urls: [], instances: [] };

        class FakeWebSocket {
            // @ts-ignore - mirrored from the real WebSocket API
            static CONNECTING = 0;
            // @ts-ignore - mirrored from the real WebSocket API
            static OPEN = 1;
            // @ts-ignore - mirrored from the real WebSocket API
            static CLOSING = 2;
            // @ts-ignore - mirrored from the real WebSocket API
            static CLOSED = 3;

            constructor(url: string) {
                this.url = url;
                this.readyState = 0;
                this.onmessage = null;
                this.onerror = null;
                this.closed = false;
                // @ts-ignore - test-only global
                window.__fakeWebSockets.urls.push(url);
                // @ts-ignore - test-only global
                window.__fakeWebSockets.instances.push(this);
            }

            close() {
                this.closed = true;
                this.readyState = 3;
            }
        }

        // @ts-ignore - replace the native constructor for this page only
        window.WebSocket = FakeWebSocket;
    });
}

/** Wait until the fake WebSocket has been constructed at least once. */
async function waitForFakeWebSocket(page: Page) {
    await page.waitForFunction(() => {
        // @ts-ignore - test-only global
        return window.__fakeWebSockets.urls.length > 0;
    });
}

test.describe('Test utilities', () => {
    setupServer();

    test.describe('Test EventStream', () => {
        test.describe.configure({ mode: 'serial' });

        // "test EventStream creation" -- registering the user logs them in,
        // which opens the event stream and emits the start event.
        test('test EventStream creation', async ({ page }) => {
            await installEventStreamProbe(page);
            await createUser(page, 'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!');

            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.start > 0;
            });
            const counts = await eventStreamCounts(page);
            expect(counts.start).toBeGreaterThan(0);
        });

        // "test EventStream auto-stop" -- a visibilitychange that calls _stop()
        // emits the stop event but must not close the stream.
        test('test EventStream auto-stop', async ({ page }) => {
            await installEventStreamProbe(page);
            await login(page, 'johndoe', 'password!');
            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.start > 0;
            });

            await setVisibilityMode(page, 'stop');
            await dispatchVisibilityChange(page);

            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.stop > 0;
            });
            const counts = await eventStreamCounts(page);
            expect(counts.stop).toBeGreaterThan(0);
            expect(counts.close).toBe(0);
        });

        // "test EventStream auto-start" -- once stopped, a visibilitychange
        // that calls _start() emits the start event again.
        test('test EventStream auto-start', async ({ page }) => {
            await installEventStreamProbe(page);
            await login(page, 'johndoe', 'password!');
            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.start > 0;
            });

            // Put the stream into the stopped state that the original spec left
            // it in after the auto-stop test.
            await setVisibilityMode(page, 'stop');
            await dispatchVisibilityChange(page);
            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.stop > 0;
            });

            await setVisibilityMode(page, 'start');
            await dispatchVisibilityChange(page);

            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.start > 1;
            });
            const counts = await eventStreamCounts(page);
            expect(counts.start).toBeGreaterThan(1);
        });

        // "test EventStream shutdown" -- close() emits both stop and close.
        test('test EventStream shutdown', async ({ page }) => {
            await installEventStreamProbe(page);
            await login(page, 'johndoe', 'password!');
            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.start > 0;
            });

            await page.evaluate(() => {
                // @ts-ignore - window.girder is available at runtime
                window.girder.utilities.eventStream.close();
            });

            await page.waitForFunction(() => {
                // @ts-ignore - test-only global
                return window.__eventStreamTest.stop > 0 && window.__eventStreamTest.close > 0;
            });
            const counts = await eventStreamCounts(page);
            expect(counts.stop).toBeGreaterThan(0);
            expect(counts.close).toBeGreaterThan(0);
        });

        // New (5.x): the WebSocket is opened against the notification channel
        // with the current auth token as a query parameter.  This behavior did
        // not exist in the 3.x SSE transport (and was untested there).
        test('builds the websocket URL from the notification root and current token', async ({ page }) => {
            await installFakeWebSocket(page);
            await login(page, 'johndoe', 'password!');
            await waitForFakeWebSocket(page);

            const result = await page.evaluate(() => {
                // @ts-ignore - test-only global
                const urls: string[] = window.__fakeWebSockets.urls;
                // @ts-ignore - window.girder is available at runtime
                const token = window.girder.auth.getCurrentToken();
                return { urls, token };
            });

            // Exactly one socket is opened on login.
            expect(result.urls).toHaveLength(1);
            const url = result.urls[0];
            // The path names the current user's notification channel (the
            // server registers this route at /notifications/me), and the token
            // query parameter matches the logged-in user's token.
            expect(url).toContain('/notifications/me?token=');
            expect(url.endsWith(`/notifications/me?token=${result.token}`)).toBe(true);
            // The event stream targets the same origin as the app, so the URL
            // is a path (not an absolute ws:// or http:// URL).
            expect(url.startsWith('/')).toBe(true);
        });

        // New (5.x): inbound websocket frames are JSON-parsed and re-emitted as
        // `g:event.<type>` Backbone events carrying the parsed payload.
        test('parses websocket messages and emits typed events', async ({ page }) => {
            await installFakeWebSocket(page);
            await login(page, 'johndoe', 'password!');
            await waitForFakeWebSocket(page);

            const payload = await page.evaluate(() => {
                return new Promise((resolve) => {
                    // @ts-ignore - window.girder is available at runtime
                    const eventStream = window.girder.utilities.eventStream;
                    eventStream.once('g:event.someTestType', (obj: unknown) => resolve(obj));
                    eventStream._onMessage({
                        data: JSON.stringify({ type: 'someTestType', value: 42 }),
                    });
                });
            }) as { type: string; value: number };

            expect(payload.type).toBe('someTestType');
            expect(payload.value).toBe(42);
        });

        // New (5.x): a frame that is not valid JSON emits `g:error` and does
        // not produce a typed `g:event.*` event.
        test('emits g:error for invalid JSON websocket messages', async ({ page }) => {
            await installFakeWebSocket(page);
            await login(page, 'johndoe', 'password!');
            await waitForFakeWebSocket(page);

            const result = await page.evaluate(() => {
                // @ts-ignore - window.girder is available at runtime
                const eventStream = window.girder.utilities.eventStream;
                let errorFired = false;
                let typedFired = false;
                eventStream.once('g:error', () => { errorFired = true; });
                eventStream.on('g:event.invalidJsonTest', () => { typedFired = true; });
                eventStream._onMessage({ data: 'this is not json' });
                // All handlers above are synchronous.
                return { errorFired, typedFired };
            });

            expect(result.errorFired).toBe(true);
            expect(result.typedFired).toBe(false);
        });

        // New (5.x): calling open() while the stream is already started must
        // not open a second websocket, and the state stays 'started'.
        test('does not open a second websocket when opened while already started', async ({ page }) => {
            await installFakeWebSocket(page);
            await login(page, 'johndoe', 'password!');
            await waitForFakeWebSocket(page);

            const result = await page.evaluate(() => {
                // @ts-ignore - window.girder is available at runtime
                const eventStream = window.girder.utilities.eventStream;
                eventStream.open();
                return {
                    // @ts-ignore - test-only global
                    urlCount: window.__fakeWebSockets.urls.length,
                    state: eventStream._state,
                };
            });

            expect(result.urlCount).toBe(1);
            expect(result.state).toBe('started');
        });

        // New (5.x): _stop() closes the underlying websocket, forgets it, and
        // moves the stream to the 'stopped' state.
        test('closes and clears the websocket on stop', async ({ page }) => {
            await installFakeWebSocket(page);
            await login(page, 'johndoe', 'password!');
            await waitForFakeWebSocket(page);

            const result = await page.evaluate(() => {
                // @ts-ignore - window.girder is available at runtime
                const eventStream = window.girder.utilities.eventStream;
                eventStream._stop();
                // @ts-ignore - test-only global
                const instance = window.__fakeWebSockets.instances[0];
                return {
                    closed: instance.closed,
                    websocketCleared: eventStream._websocket === null,
                    state: eventStream._state,
                };
            });

            expect(result.closed).toBe(true);
            expect(result.websocketCleared).toBe(true);
            expect(result.state).toBe('stopped');
        });

        // New (5.x): _onError is intentionally a no-op at present (it carries a
        // TODO to handle errors), so it must neither throw nor emit anything.
        // If error handling is implemented later, this test should be replaced
        // with one asserting the new behavior.
        test('_onError is a no-op that does not throw or emit', async ({ page }) => {
            await installFakeWebSocket(page);
            await login(page, 'johndoe', 'password!');
            await waitForFakeWebSocket(page);

            const result = await page.evaluate(() => {
                // @ts-ignore - window.girder is available at runtime
                const eventStream = window.girder.utilities.eventStream;
                let errorFired = false;
                let disableFired = false;
                eventStream.on('g:error', () => { errorFired = true; });
                eventStream.on('g:eventStream.disable', () => { disableFired = true; });
                let threw = false;
                try {
                    eventStream._onError();
                } catch (e) {
                    threw = true;
                }
                return { threw, errorFired, disableFired };
            });

            expect(result.threw).toBe(false);
            expect(result.errorFired).toBe(false);
            expect(result.disableFired).toBe(false);
        });
    });

    test.describe('test showDownload traversal', () => {
        // "checks the root view" -- traversal follows parentView all the way to
        // the root, so the root's false value wins for both child and parent.
        test('checks the root view', async ({ page }) => {
            const result = await page.evaluate(() => {
                // @ts-ignore - window.girder is available at runtime
                const { showDownload } = window.girder.utilities;
                const rootView = { showDownload: () => false };
                const parentView = { showDownload: () => true, parentView: rootView };
                const childView = { parentView };
                return {
                    child: showDownload(childView),
                    parent: showDownload(parentView),
                };
            });

            expect(result.child).toBe(false);
            expect(result.parent).toBe(false);
        });

        // "defaults to true"
        test('defaults to true', async ({ page }) => {
            const result = await page.evaluate(() => {
                // @ts-ignore - window.girder is available at runtime
                const { showDownload } = window.girder.utilities;
                return showDownload({});
            });

            expect(result).toBe(true);
        });
    });
});
