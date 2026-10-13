import { Page, expect, test } from '@playwright/test';

import { setupServer } from '../server';
import { createUser, login } from '../util';

/**
 * Ported from 3.x-maintenance: plugins/jobs/plugin_tests/jobsSpec.js
 *
 * The original spec was almost entirely a unit test of the jobs client widgets:
 * it mocked `JobModel.fetch`, instantiated `JobListWidget` directly against a
 * fake collection, and drove the widgets through the client event stream. That
 * style is preserved here by running the same widget code inside the page via
 * `page.evaluate`, which is how other ports (for example utilities.spec.ts)
 * exercise client-only modules.
 *
 * The shared server/database is created once per describe; the "job detail"
 * describe mocks out fetching so it does not need a real job, while the "job
 * list" describe registers an admin and uses the real jobs plugin routes.
 */

/**
 * Run `fn` in the page with the jobs plugin namespace available, forwarding
 * `arg` and resolving with its return value.
 */
async function inPage<T, A>(page: Page, fn: (jobs: any, arg: A) => T, arg?: A): Promise<T> {
    return await page.evaluate(
        ({ fnBody, arg: innerArg }) => {
            // @ts-ignore - window.girder is available at runtime
            const jobs = window.girder.plugins.jobs;
            // eslint-disable-next-line no-new-func
            const fn = new Function('jobs', 'arg', `return (${fnBody})(jobs, arg);`) as (jobs: unknown, arg: unknown) => unknown;
            return fn(jobs, innerArg);
        },
        { fnBody: fn.toString(), arg },
    ) as T;
}

/**
 * Run `fn` in the page as an async function.
 */
async function inPageAsync<T, A>(page: Page, fn: (jobs: any, arg: A) => Promise<T>, arg?: A): Promise<T> {
    return await page.evaluate(
        async ({ fnBody, arg: innerArg }) => {
            // @ts-ignore - window.girder is available at runtime
            const jobs = window.girder.plugins.jobs;
            // eslint-disable-next-line no-new-func
            const fn = new Function('jobs', 'arg', `return (${fnBody})(jobs, arg);`) as (jobs: unknown, arg: unknown) => Promise<unknown>;
            return await fn(jobs, innerArg);
        },
        { fnBody: fn.toString(), arg },
    ) as T;
}

test.describe('Unit test the job detail widget', () => {
    setupServer();

    test('render a job, react to events, and report finished status', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'User', 'password!');

        // Create the mocked job, install it, and navigate to its detail page.
        await inPage(page, (jobs) => {
            const girder = (window as any).girder;
            const JobStatus = jobs.JobStatus;

            (window as any).__jobInfo = {
                _id: 'foo',
                title: 'My batch job',
                // A type is required by plugins that wrap JobStatus.isCancelable
                // (for example slicer_cli_web), which inspect job.get('type').
                type: 'my_job_type',
                status: JobStatus.INACTIVE,
                log: ['Hello world\n', 'goodbye world'],
                updated: '2015-01-12T12:00:12Z',
                created: '2015-01-12T12:00:00Z',
                when: '2015-01-12T12:00:00Z',
                timestamps: [
                    { status: JobStatus.QUEUED, time: '2015-01-12T12:00:02Z' },
                    { status: JobStatus.RUNNING, time: '2015-01-12T12:00:03Z' },
                    { status: JobStatus.SUCCESS, time: '2015-01-12T12:00:12Z' },
                ],
            };

            // Mock fetch to simulate fetching a job without a server round trip.
            jobs.models.JobModel.prototype.fetch = function () {
                this.set((window as any).__jobInfo);
                this.trigger('g:fetched');
                return girder.$.Deferred().resolve((window as any).__jobInfo).promise();
            };

            girder.router.navigate('job/foo', { trigger: true });
        });

        await expect(page.locator('.g-job-info-key').first()).toBeVisible();

        // Verify initial rendering and the absence of a cancel button.
        await expect(page.locator('.g-monospace-viewer[property="kwargs"]')).toHaveCount(0);
        await expect(page.locator('.g-monospace-viewer[property="log"]')).toHaveText('Hello world\ngoodbye world');
        await expect(page.locator('.g-job-info-value[property="_id"]')).toHaveText('foo');
        await expect(page.locator('.g-job-info-value[property="title"]')).toHaveText('My batch job');
        await expect(page.locator('.g-job-info-value[property="when"]')).toContainText('January 12, 2015');
        await expect(page.locator('.g-job-status-badge')).toContainText('Inactive');
        await expect(page.locator('button.g-job-cancel')).toHaveCount(0);

        // Timeline: 3 segments, 4 points, labels 0 s .. 12 s.
        await expect(page.locator('.g-timeline-segment')).toHaveCount(3);
        await expect(page.locator('.g-timeline-point')).toHaveCount(4);
        await expect(page.locator('.g-timeline-start-label')).toHaveText('0 s');
        await expect(page.locator('.g-timeline-end-label')).toHaveText('12 s');

        // The final point's background color is the SUCCESS color.
        const pointColor = await page.evaluate(() => {
            const girder = (window as any).girder;
            const point = document.querySelectorAll('.g-timeline-point')[3] as HTMLElement;
            const rgb = getComputedStyle(point).backgroundColor;
            const match = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/)!;
            const toHex = (c: string) => {
                const hex = parseInt(c, 10).toString(16);
                return hex.length === 1 ? `0${hex}` : hex;
            };
            const asHex = `#${toHex(match[1])}${toHex(match[2])}${toHex(match[3])}`;
            return {
                asHex,
                successColor: girder.plugins.jobs.JobStatus.color(girder.plugins.jobs.JobStatus.SUCCESS),
            };
        });
        expect(pointColor.asHex).toBe(pointColor.successColor);

        // A job_status event for this job updates the badge, but one for a
        // different job does not.
        await inPage(page, (jobs) => {
            const girder = (window as any).girder;
            girder.utilities.eventStream.trigger('g:event.job_status', {
                data: { _id: 'foo', status: jobs.JobStatus.SUCCESS },
            });
        });
        await expect(page.locator('.g-job-status-badge')).toContainText('Success');

        await inPage(page, (jobs) => {
            const girder = (window as any).girder;
            girder.utilities.eventStream.trigger('g:event.job_status', {
                data: { _id: 'bar', status: jobs.JobStatus.QUEUED },
            });
        });
        await expect(page.locator('.g-job-status-badge')).toContainText('Success');

        // Log output events: overwrite replaces the log, append escapes its text.
        await inPage(page, () => {
            const girder = (window as any).girder;
            girder.utilities.eventStream.trigger('g:event.job_log', {
                data: { _id: 'foo', overwrite: true, text: 'overwritten log' },
            });
        });
        await expect(page.locator('.g-monospace-viewer[property="log"]')).toHaveText('overwritten log');

        await inPage(page, () => {
            const girder = (window as any).girder;
            girder.utilities.eventStream.trigger('g:event.job_log', {
                data: { _id: 'foo', overwrite: false, text: '<script type="text/javascript">xss probe!</script>' },
            });
        });
        await expect(page.locator('.g-monospace-viewer[property="log"]')).toHaveText(
            'overwritten log<script type="text/javascript">xss probe!</script>',
        );
        // The appended text must be escaped, not interpreted as HTML.
        await expect(page.locator('.g-monospace-viewer[property="log"] script')).toHaveCount(0);

        // A status change back to QUEUED, then an eventStream restart refetches
        // the (now ERROR) job and updates the badge.
        await inPage(page, (jobs) => {
            const girder = (window as any).girder;
            girder.utilities.eventStream.trigger('g:event.job_status', {
                data: { _id: 'foo', status: jobs.JobStatus.QUEUED },
            });
        });
        await expect(page.locator('.g-job-status-badge')).toContainText('Queued');

        await inPage(page, (jobs) => {
            const girder = (window as any).girder;
            (window as any).__jobInfo.status = jobs.JobStatus.ERROR;
            girder.utilities.eventStream.trigger('g:eventStream.start', {});
        });
        await expect(page.locator('.g-job-status-badge')).toContainText('Error');

        // JobStatus.finished reports the expected values.
        const finished = await inPage(page, (jobs) => {
            const JobStatus = jobs.JobStatus;
            return [
                JobStatus.finished(JobStatus.QUEUED),
                JobStatus.finished(JobStatus.RUNNING),
                JobStatus.finished(JobStatus.ERROR),
                JobStatus.finished(JobStatus.SUCCESS),
                JobStatus.finished(JobStatus.CANCELED),
            ];
        });
        expect(finished).toEqual([false, false, true, true, true]);
    });
});

test.describe('Unit test the job list widget', () => {
    setupServer();

    /**
     * Instantiate a JobListWidget in the page into a fresh container and return
     * its cid. Waits until the initial fetch has rendered twice (matching the
     * original spec's renderDataSpy.callCount >= 2 gate).
     */
    async function makeWidget(page: Page, settings: Record<string, unknown>) {
        return await inPageAsync(page, async (jobs, opts) => {
            const el = document.createElement('div');
            el.id = 'job-list-test-container';
            document.body.appendChild(el);

            // Wrap _renderData on the prototype so we can wait for the initial
            // asynchronous fetch render, matching the original spec's
            // renderDataSpy.callCount >= 2 gate. JobListWidget calls the
            // prototype method during construction, so the wrapper must be
            // installed before instantiating.
            const proto = jobs.views.JobListWidget.prototype as any;
            const original = proto._renderData;
            let renderCount = 0;
            proto._renderData = function (...args: unknown[]) {
                renderCount += 1;
                return original.apply(this, args);
            };

            const widget = new jobs.views.JobListWidget({
                el,
                parentView: null,
                ...opts,
            });
            (window as any).__jobListWidget = widget;
            (window as any).__jobListRenderData = () => {
                proto._renderData = original;
                return renderCount;
            };

            // Wait for the initial async fetch/render to settle (>= 2 renders).
            await new Promise<void>((resolve) => {
                const check = () => {
                    if (renderCount >= 2) {
                        resolve();
                    } else {
                        setTimeout(check, 25);
                    }
                };
                check();
            });
            return widget.cid;
        }, settings);
    }

    test('register the admin user', async ({ page }) => {
        await createUser(page, 'admin', 'admin@girder.test', 'Quota', 'Admin', 'password!');
    });

    test('show a job list widget and react to status events', async ({ page }) => {
        await login(page, 'admin', 'password!');
        await makeWidget(page, {
            filter: {},
            showGraphs: true,
            showFilters: true,
            showPageSizeSelector: true,
        });

        await expect(page.locator('#job-list-test-container .g-jobs-list-table > tbody > tr')).toHaveCount(0);

        // Add three jobs in explicit statuses.
        await inPage(page, (jobs) => {
            const widget = (window as any).__jobListWidget;
            const statuses = [jobs.JobStatus.QUEUED, jobs.JobStatus.RUNNING, jobs.JobStatus.SUCCESS];
            statuses.forEach((status: number, i: number) => {
                widget.collection.add(new jobs.models.JobModel({
                    _id: `foo${i}`,
                    title: `My batch job ${i}`,
                    type: 'my_job_type',
                    status,
                    updated: `2015-01-12T12:00:0${i}`,
                    created: `2015-01-12T12:00:0${i}`,
                    when: `2015-01-12T12:00:0${i}`,
                }));
            });
        });

        const rows = page.locator('#job-list-test-container .g-jobs-list-table > tbody > tr');
        await expect(rows).toHaveCount(3);

        // Reverse chronological order: job 2 (Success), job 1 (Running), job 0 (Queued).
        await expect(rows.nth(0)).toContainText('My batch job 2');
        await expect(rows.nth(0)).toContainText('Success');
        await expect(rows.nth(1)).toContainText('My batch job 1');
        await expect(rows.nth(1)).toContainText('Running');
        await expect(rows.nth(2)).toContainText('My batch job 0');
        await expect(rows.nth(2)).toContainText('Queued');

        // A job_status event for the last job (foo0) updates its row.
        await inPage(page, (jobs) => {
            const girder = (window as any).girder;
            const widget = (window as any).__jobListWidget;
            const job = widget.collection.get('foo0');
            girder.utilities.eventStream.trigger('g:event.job_status', {
                data: {
                    ...job.attributes,
                    status: jobs.JobStatus.ERROR,
                },
            });
        });
        await expect(rows.nth(2).locator('td.g-job-status-cell')).toHaveText('Error');

        // A job_created event triggers a refetch; since the server has no jobs,
        // the locally added jobs are cleared and the empty message shows.
        await inPage(page, (jobs) => {
            const girder = (window as any).girder;
            girder.utilities.eventStream.trigger('g:event.job_created', {
                data: {
                    _id: 'foo4',
                    title: 'My batch job 4',
                    type: 'my_job_type',
                    status: jobs.JobStatus.ERROR,
                    updated: '2015-01-12T12:00:04',
                    created: '2015-01-12T12:00:04',
                    when: '2015-01-12T12:00:04',
                },
            });
        });
        await expect(page.locator('#job-list-test-container .g-no-job-record')).toBeVisible();
    });

    test('filter jobs by status and type', async ({ page }) => {
        await login(page, 'admin', 'password!');
        await makeWidget(page, {
            filter: {},
            showGraphs: true,
            showFilters: true,
            showPageSizeSelector: true,
        });

        await expect(page.locator('#job-list-test-container .g-jobs-list-table > tbody > tr')).toHaveCount(0);

        const result = await inPage(page, () => {
            const widget = (window as any).__jobListWidget;
            widget.typeFilterWidget.setItems({ 'type A': true, 'type B': true, 'type C': false });

            const countChecked = () =>
                widget.$('.g-job-filter-container .type .dropdown ul li input[type="checkbox"]:checked').length;

            const afterSet = countChecked();
            widget.$('.g-job-filter-container .type .dropdown ul li input').first().trigger('click');
            const afterUncheck = countChecked();
            widget.$('.g-job-filter-container .type .dropdown .g-job-checkall input').trigger('click');
            const afterCheckAll = countChecked();
            const checkAllChecked = widget.$('.g-job-filter-container .type .dropdown .g-job-checkall input').is(':checked');

            widget.$('.g-job-filter-container .status .dropdown .g-job-checkall input').trigger('click');
            const statusChecked = widget.$('.g-job-filter-container .status .dropdown ul li input[type="checkbox"]:checked').length;

            widget.$('.g-page-size').val(50).trigger('change');
            return {
                afterSet,
                afterUncheck,
                afterCheckAll,
                checkAllChecked,
                statusChecked,
                pageLimit: widget.collection.pageLimit,
            };
        });

        expect(result.afterSet).toBe(2);
        expect(result.afterUncheck).toBe(1);
        expect(result.afterCheckAll).toBe(3);
        expect(result.checkAllChecked).toBe(true);
        expect(result.statusChecked).toBe(0);
        expect(result.pageLimit).toBe(50);
    });

    test('trigger a click event on a job link', async ({ page }) => {
        await login(page, 'admin', 'password!');
        await makeWidget(page, {
            filter: {},
            triggerJobClick: true,
            showGraphs: true,
            showFilters: true,
            showPageSizeSelector: true,
        });

        await inPage(page, (jobs) => {
            const widget = (window as any).__jobListWidget;
            const statuses = [jobs.JobStatus.QUEUED, jobs.JobStatus.RUNNING, jobs.JobStatus.SUCCESS];
            statuses.forEach((status: number, i: number) => {
                widget.collection.add(new jobs.models.JobModel({
                    _id: `foo${i}`,
                    title: `My batch job ${i}`,
                    type: 'my_job_type',
                    status,
                    updated: `2015-01-12T12:00:0${i}`,
                    created: `2015-01-12T12:00:0${i}`,
                    when: `2015-01-12T12:00:0${i}`,
                }));
            });
        });

        await expect(page.locator('#job-list-test-container .g-jobs-list-table > tbody > tr')).toHaveCount(3);

        const fired = await inPage(page, () => {
            const widget = (window as any).__jobListWidget;
            let fired = false;
            widget.on('g:jobClicked', () => {
                fired = true;
            });
            widget.$('.g-job-trigger-link').trigger('click');
            return fired;
        });
        expect(fired).toBe(true);
    });

    test('use the job list widget in all jobs mode', async ({ page }) => {
        await login(page, 'admin', 'password!');
        await makeWidget(page, {
            filter: {},
            allJobsMode: true,
            showGraphs: true,
            showFilters: true,
            showPageSizeSelector: true,
        });

        const resourceName = await inPage(page, () => (window as any).__jobListWidget.collection.resourceName);
        expect(resourceName).toEqual('job/all');
    });

    test('cancel jobs from the job list', async ({ page }) => {
        await login(page, 'admin', 'password!');
        await makeWidget(page, {
            filter: {},
            triggerJobClick: true,
            showGraphs: true,
            showFilters: true,
            showPageSizeSelector: true,
        });

        await inPage(page, (jobs) => {
            const widget = (window as any).__jobListWidget;
            [1, 2, 3].forEach((i: number) => {
                widget.collection.add(new jobs.models.JobModel({
                    _id: `foo${i}`,
                    title: `My batch job ${i}`,
                    type: 'my_job_type',
                    status: i,
                    updated: `2015-01-12T12:00:0${i}`,
                    created: `2015-01-12T12:00:0${i}`,
                    when: `2015-01-12T12:00:0${i}`,
                }));
            });
        });

        await expect(page.locator('#job-list-test-container .g-jobs-list-table > tbody > tr')).toHaveCount(3);

        const result = await inPage(page, () => {
            const widget = (window as any).__jobListWidget;
            const menuDisabledBefore = widget.$('.g-job-check-menu-button').is(':disabled');

            // Click the checkbox DOM elements directly (as the original did).
            widget.$('input:checkbox:not(:checked).g-job-checkbox')[0].click();
            widget.$('input:checkbox:not(:checked).g-job-checkbox')[0].click();
            widget.$('input:checkbox:not(:checked).g-job-checkbox')[0].click();

            const menuDisabledAfter = widget.$('.g-job-check-menu-button').is(':disabled');
            const allChecked = widget.$('.g-job-checkbox-all').is(':checked');

            widget.$('.g-job-checkbox-all')[0].click();
            const uncheckedAfterToggleOff = widget.$('input:checkbox:not(:checked).g-job-checkbox').length;

            widget.$('.g-job-checkbox-all')[0].click();
            const uncheckedAfterToggleOn = widget.$('input:checkbox:not(:checked).g-job-checkbox').length;

            widget.$('.g-jobs-list-cancel').trigger('click');

            return {
                menuDisabledBefore,
                menuDisabledAfter,
                allChecked,
                uncheckedAfterToggleOff,
                uncheckedAfterToggleOn,
            };
        });

        expect(result.menuDisabledBefore).toBe(true);
        expect(result.menuDisabledAfter).toBe(false);
        expect(result.allChecked).toBe(true);
        expect(result.uncheckedAfterToggleOff).toBe(3);
        expect(result.uncheckedAfterToggleOn).toBe(0);
    });

    test('render timing history and time series charts', async ({ page }) => {
        await login(page, 'admin', 'password!');
        await makeWidget(page, {
            filter: {},
            showGraphs: true,
            showFilters: true,
            showPageSizeSelector: true,
        });

        await inPage(page, (jobs) => {
            const widget = (window as any).__jobListWidget;
            ['one', 'two', 'three'].forEach((type: string, i: number) => {
                widget.collection.add(new jobs.models.JobModel({
                    _id: `foo${i}`,
                    title: `My batch job ${i}`,
                    status: jobs.JobStatus.ERROR,
                    type,
                    timestamps: [
                        { status: jobs.JobStatus.QUEUED, time: '2017-03-10T18:31:59.008Z' },
                        { status: jobs.JobStatus.RUNNING, time: '2017-03-10T18:32:06.190Z' },
                        { status: jobs.JobStatus.ERROR, time: '2017-03-10T18:32:34.760Z' },
                    ],
                    updated: '2017-03-10T18:32:34.760Z',
                    created: '2017-03-10T18:31:59.008Z',
                    when: '2017-03-10T18:31:59.008Z',
                }));
            });
            // Show the timing history tab (triggers the async Vega render).
            widget.$('.g-jobs.nav.nav-tabs li a[name="timing-history"]').tab('show');
        });

        const timingPaths = page.locator(
            '#job-list-test-container .g-jobs-graph svg .mark-rect.timing path',
        );
        await expect(timingPaths).toHaveCount(9);

        await inPage(page, () => {
            const widget = (window as any).__jobListWidget;
            widget.$('.g-jobs.nav.nav-tabs li a[name="time"]').tab('show');
        });

        const circlePaths = page.locator(
            '#job-list-test-container .g-jobs-graph svg .mark-symbol.circle path',
        );
        await expect(circlePaths).toHaveCount(3);

        // Unchecking all phases clears the time-series graph.
        await inPage(page, () => {
            const widget = (window as any).__jobListWidget;
            widget.$('.g-job-filter-container .timing .dropdown .g-job-checkall input').trigger('click');
        });
        await expect(circlePaths).toHaveCount(0);
    });

    test('instantiate without graphs, filters, or page size selector', async ({ page }) => {
        await login(page, 'admin', 'password!');
        await makeWidget(page, { filter: {} });

        const counts = await inPage(page, () => {
            const widget = (window as any).__jobListWidget;
            return {
                tabs: widget.$('.g-jobs.nav.nav-tabs').length,
                filters: widget.$('.g-job-filter-container').length,
                pageSize: widget.$('.g-page-size-container').length,
            };
        });
        expect(counts.tabs).toBe(0);
        expect(counts.filters).toBe(0);
        expect(counts.pageSize).toBe(0);
    });
});
