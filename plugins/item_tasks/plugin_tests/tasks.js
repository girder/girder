girderTest.addCoveredScripts([
    '/clients/web/static/built/plugins/jobs/plugin.min.js',
    '/clients/web/static/built/plugins/worker/plugin.min.js',
    '/clients/web/static/built/plugins/item_tasks/plugin.min.js'
]);

girderTest.importStylesheet('/static/built/plugins/jobs/plugin.min.css');
girderTest.importStylesheet('/static/built/plugins/worker/plugin.min.css');
girderTest.importStylesheet('/static/built/plugins/item_tasks/plugin.min.css');

girderTest.startApp();

describe('Create an item task', function () {
    it('register an admin', girderTest.createUser(
        'admin', 'admin@example.com', 'Admin', 'Admin', 'password'
    ));

    it('go to collection page', function () {
        $('ul.g-global-nav .g-nav-link[g-target="collections"]').click();
    });

    it('create collection and folder', girderTest.createCollection('task test', '', 'tasks'));

    it('create item', function () {
        runs(function () {
            $('.g-folder-list-link').click();
        });

        waitsFor(function () {
            return $('.g-empty-parent-message:visible').length > 0;
        }, 'folder empty list to appear');

        runs(function () {
            $('.g-folder-actions-button').click();
            $('.g-folder-actions-menu .g-create-item').click();
        });

        girderTest.waitForDialog();

        runs(function () {
            $('.modal-dialog #g-name').val('task placeholder');
            $('.modal-dialog .g-save-item').click();
        });

        waitsFor(function () {
            return $('.g-item-list-link').text().indexOf('task placeholder') !== -1;
        }, 'item to appear in the list');
    });
});

describe('Auto-configure the item task', function () {
    it('navigate to the item', function () {
        $('.g-item-list-link:first').click();

        waitsFor(function () {
            return $('.g-item-files .g-file-list').length > 0;
        }, 'item view to render');
    });

    it('run configuration job', function () {
        $('.g-item-actions-button').click();
        $('.g-item-actions-menu .g-configure-item-task').click();

        girderTest.waitForDialog();

        runs(function () {
            $('.modal-dialog .g-slicer-cli-docker-image').val('me/my_image:latest');
            $('.modal-dialog .g-slicer-cli-docker-args').val('["foo", "bar"]');
            $('.modal-dialog button.btn.btn-success[type="submit"]').click();
        });

        waitsFor(function () {
            return $('.g-job-info-key').length > 0;
        }, 'navigation to the configuration job');

        waitsFor(function () {
            return $('.g-job-status-badge').attr('status') === 'success';
        }, 'job success status', 10000);
    });
});

describe('Run the item task', function () {
    it('navigate to task', function () {
        $('.g-nav-link[g-target="item_tasks"]').click();

        waitsFor(function (){
            return $('.g-execute-task-link').length > 0;
        }, 'task list to be rendered');

        runs(function () {
            expect($('.g-execute-task-link').length).toBe(1);
            expect($('.g-execute-task-link').text()).toBe('PET phantom detector CLI');
            window.location.assign($('a.g-execute-task-link').attr('href'));
        });

        waitsFor(function () {
            return $('.g-task-description-container').length > 0;
        }, 'task run view to display');

        runs(function () {
            expect($('.g-task-description-container').text()).toContain(
                'Detects positions of PET/CT pocket phantoms in PET image.');
            expect($('.g-inputs-container').length).toBe(1);
            expect($('.g-inputs-container .g-control-item').length).toBe(9);
        });
    });

    it('configure task inputs', function () {
        $('.g-inputs-container .g-select-file-button').click();
        girderTest.waitForDialog();

        waitsFor(function () {
            return $('.modal-dialog #g-root-selector:visible').length > 0;
        }, 'input root selector to appear');

        runs(function () {
            // Select our collection for the input item
            var id = $('.modal-dialog #g-root-selector option[data-group="Collections"]').attr('value');
            $('.modal-dialog #g-root-selector').val(id).trigger('change');
        });

        waitsFor(function () {
            return $('.modal-dialog .g-folder-list-link').text().indexOf('tasks') !== -1;
        }, 'hierarchy widget to update for input root');

        runs(function () {
            $('.modal-dialog .g-folder-list-link:first').click();
        });

        waitsFor(function () {
            return $('.modal-dialog .g-item-list-link').length > 0;
        }, 'folder nav in input selection widget');

        runs(function () {
            expect($('.modal-dialog #g-selected-model').val()).toBe('');
            $('.modal-dialog .g-item-list-link').click();
            expect($('.modal-dialog #g-selected-model').val()).not.toBe('');
            $('.modal-dialog .g-submit-button').click();
        });

        girderTest.waitForLoad();
    });

    it('configure task output', function () {
        $('.g-outputs-container .g-select-file-button').click();
        girderTest.waitForDialog();

        waitsFor(function () {
            return $('.modal-dialog .g-folder-list-link').length === 2;
        }, 'user public and private folder to appear in the list');

        runs(function () {
            // check invalid parent
            $('.modal-dialog .g-submit-button').click();
            expect($('.g-validation-failed-message').text()).toMatch(/Invalid parent type/);
            $('.modal-dialog .g-folder-list-link:first').click();
        });

        waitsFor(function () {
            return $('.modal-dialog .g-folder-list-link').length === 0;
        }, 'folder nav in output selection widget');

        runs(function () {
            // check no name provided
            $('.modal-dialog .g-submit-button').click();
            expect($('.g-validation-failed-message').text()).toMatch(/Please provide an item name/);

            $('#g-input-element').val('out.txt');
            $('.modal-dialog .g-submit-button').click();
        });

        girderTest.waitForLoad();
    });

    it('run the task', function () {
        $('.g-run-task').click();

        waitsFor(function () {
            return $('.g-item-tasks-job-info-container').length > 0;
        }, 'job page to display');

        runs(function () {
            expect($('.g-item-task-inputs-container ul>li').length).toBe(9);
            expect($('.g-item-task-outputs-container ul>li').length).toBe(1);
        });
    });
});

describe('Auto-configure the JSON item task folder', function () {
    it('go to collection page', function () {
        $('ul.g-global-nav .g-nav-link[g-target="collections"]').click();
    });

    it('create collection and folder', girderTest.createCollection('json task test', '', 'tasks'));

    it('navigate to the folder', function () {
        runs(function () {
            $('.g-folder-list-link').click();
        });

        waitsFor(function () {
            return $('.g-empty-parent-message:visible').length > 0;
        }, 'folder empty list to appear');
    });

    it('run configuration job', function () {
        $('.g-folder-actions-button').click();
        $('.g-folder-actions-menu .g-create-docker-tasks').click();

        girderTest.waitForDialog();

        runs(function () {
            $('.modal-dialog .g-configure-docker-image').val('me/my_image:latest');
            $('.modal-dialog button.btn.btn-success[type="submit"]').click();
        });

        waitsFor(function () {
            return $('.g-job-info-key').length > 0;
        }, 'navigation to the configuration job');

        waitsFor(function () {
            return $('.g-job-status-badge').attr('status') === 'success';
        }, 'job success status', 10000);
    });
});


describe('Navigate to the new JSON task', function () {
    it('navigate to task', function () {
        $('.g-nav-link[g-target="item_tasks"]').click();

        waitsFor(function (){
            return $('.g-execute-task-link').length > 0;
        }, 'task list to be rendered');

        runs(function () {
            expect($('.g-execute-task-link').length).toBe(3);
            expect($('.g-execute-task-link').eq(0).text()).toBe('me/my_image:latest 0');
            expect($('.g-execute-task-link').eq(1).text()).toBe('me/my_image:latest 1');
            window.location.assign($('a.g-execute-task-link').eq(0).attr('href'));
        });

        waitsFor(function () {
            return $('.g-task-description-container').length > 0;
        }, 'task run view to display');

        runs(function () {
            expect($('.g-task-description-container').text()).toContain(
                'Task 1 description');
            expect($('.g-inputs-container').length).toBe(0);
        });
    });
});
