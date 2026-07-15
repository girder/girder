Web Client Test Conversion Guide

We are in the girder repo (/home/ubuntu/girder), which consists of a server and web client.  We have some tests for the web client that we usually run via `tox -e web-test`. These tests use playwright and pytest fixtures, and internally, the web client is built with vite, but is an an old bootstrap / backbone based client. Girder recently had a major shift in how its web client was built; we are on girder 5.x, but the 3.x-maintenance branch has more client tests than were ported over to the new test infrastructure.  You can see of the git `3.x-maintenance` branch tests at `girder/web_client/test/spec`, only some of which have been moved to `girder/web/tests/spec`.  We would like to port the rest of these over.  We will port over tests one-at-a-time and ensure that they pass rather than try do all of them at once. `tox -e web-test` must run and pass with the new tests (and all old tests must still run and pass).  You absolutely MUST run `tox -e web-test` without errors before claiming the new tests work.

It is recommended to run `tox -e web-test` as a first step to understand how existing tests are commonly executed.

1. Context & Architecture

- Repository Scope: Girder web client test conversion targets the legacy
  3.x-maintenance branch tests (girder/web_client/test/spec) and migrates them
  into the modern Playwright + TypeScript codebase at girder/web/tests/spec.
- Build System: The client is built with Vite. Assets, plugins, and static
  files are served by a local CherryPy test harness started automatically via
  the test runner.
- Test Runner:
    - Playwright orchestrates headless browser execution (Chromium & Firefox).
    - Tests are discovered in girder/web/tests/spec/ as .spec.ts files.
    - The full suite is triggered with tox -e web-test.
- Infrastructure Helpers (girder/web/tests/util.ts):
    - setupServer(): Spins up a fresh Girder server instance for a
      test.describe block.
    - createUser(page, login, email, first, last, pass): Registers an account
      on the front page (first registered in a fresh server becomes admin).
    - login(page, login, password) / logout(page): Handles UI-based auth flows
      with mandatory delays for backend sync.
    - waitForDialog(page), delay(ms): Utilities for dialog readiness and
      post-action waits.

2. Conversion Workflow: Processing One Legacy Test

  1. Identify & Analyze: Locate the legacy spec in
     3.x-maintenance/girder/web_client/test/spec. Read its assertions, DOM
     interactions, and expectations.

  2. Group Logic: Combine related assertions into a single Playwright
     test.describe block if they test one cohesive feature. Each .describe gets
     its own fresh server instance via setupServer().

  3. Import Setup & Utilities:
     ```typescript
       import { expect, test } from '@playwright/test';
       import { createUser, delay, login, logout, waitForDialog } from
     '../util';
       import { setupServer } from '../server';
     ```

  4. Reconstruct the UI Flow (Click → Wait → Assert):
      - First User = Admin: Since each describe block starts fresh, always call
        createUser() for an admin if the test requires admin privileges before
        using admin menus.
      - Navigation: Avoid assuming direct URLs route reliably in single-page
        mode. Mirroring existing patterns is safer. For admin/console routes,
        click the header " Admin console" link first, then target the specific
        dropdown item (e.g., " Plugins").
      - Wait Strategy: UI updates and REST responses are async. Insert await
        delay(500) after logins, user creations, or clicks that trigger API
        calls. Use expect(locator).toBeVisible({ timeout: 10000 }) where content
        takes time to populate.
      - Selectors: Prefer specific Playwright role/locator methods (getByRole,
        getByText) combined with class names (.g-*). Avoid brittle XPaths or
        index-based selectors.
      - Matchers: Use standard Playwright syntax. Note that
        toHaveCountGreaterThan does not exist; use expect(await
        page.locator('.class').count()).toBeGreaterThanOrEqual(n).

  5. Draft the Test File: Write the new .spec.ts block with clear step comments
     mirroring the original test's sequence.

  6. Do not add fixed delays -- all waiting must be based on actual DOM
     changes.

3. Verification Requirements

- Exact Execution Command: Always run tox -e web-test from the repository root
  to validate changes.
- Browser Parity: Playwright executes tests sequentially across both Chromium
  and Firefox. Both must pass (e.g., 32 passed / 0 failed).
- Pass Requirement: The new test block may not leave existing suites broken.
  web-test: OK is required.
- Pre-Completion Check: Before marking the task complete, explicitly confirm
  that `tox -e web-test` runs without errors

4. File Conventions & Standards

┌───────────────────────────────────┬─────────────────────────────────┐
│ Legacy Location (3.x-maintenance) │ Target Location                 │
├───────────────────────────────────┼─────────────────────────────────┤
│ girder/web_client/test/spec/*.js  │ girder/web/tests/spec/*.spec.ts │
└───────────────────────────────────┴─────────────────────────────────┘

- Naming: Convert JavaScript naming to TypeScript. Example: adminSpec.js →
  admin.spec.ts. Maintain descriptive, kebab-case suffixes where the original
  had them.
- Directory Structure:
    - Test files live directly in girder/web/tests/spec/.
    - Shared helpers (util.ts, server.ts) remain at girder/web/tests/.
    - Imports utilize relative paths from the spec file to these helpers
      (e.g., import { ... } from '../util').
- Test File Structure:
  ```typescript
    import { expect, test } from '@playwright/test';
    import { ... } from '../util';
    import { setupServer } from '../server';

    // Group tests by feature/page (each group gets a fresh server)
    test.describe('Feature Name', () => {
      setupServer();

      test('Descriptive step title', async ({ page }) => {
        // Arrange: create users if needed, navigate
        // Act: interact with DOM
        // Assert: verify visibility, content, state
      });
    });
  ```
- Style: Keep tests sequential and self-contained. Do not rely on implicit
  global state between test() blocks within a describe. Comment complex
  navigation or timing decisions to help future maintainers understand the
  selector/delay choices.

5. Running tests

Girder depends on a fairly complex set of packages and services. The existing tests all pass when run via `tox -e web-test`.  Running tests directly with npx or playwright is more complex; while it can be done, it is probably not worth the hassle.

6. Girder 3 and Girder 5 difference

- There is a migration guide at docs/migration-guide.rst that discusses some of the differences.

- Gridfs was removed between Girder 3 and Girder 5.  We do not need any gridfs
specific tests.

- The Admin settings page is largely read-only in Girder 5; any test that expects to edit those settings is likely not to be valid.
