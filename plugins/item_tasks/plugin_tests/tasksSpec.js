girderTest.importPlugin('jobs', 'worker', 'item_tasks');
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
            return $('.g-item-list-link:contains("task placeholder")').length > 0;
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
            $('.modal-dialog .g-configure-slicer-cli-task-tab > a').click();
            $('.modal-dialog .g-slicer-cli-docker-image').val('me/my_image:latest');
            $('.modal-dialog .g-slicer-cli-docker-args').val('["foo", "bar"]');
            $('.modal-dialog button.btn.btn-success[type="submit"]').click();
        });

        waitsFor(function () {
            return $('.g-job-info-key').length > 0;
        }, 'navigation to the configuration job');

        waitsFor(function () {
            return $('.g-job-status-badge').attr('status') === 'success';
        }, 'job success status');
    });
});

describe('Run the item task', function () {
    it('navigate to task', function () {
        $('.g-nav-link[g-target="item_tasks"]').click();

        waitsFor(function () {
            return $('.g-execute-task-link').length > 0;
        }, 'task list to be rendered');

        runs(function () {
            expect($('.g-execute-task-link').length).toBe(1);
            expect($('.g-execute-task-link .g-execute-task-link-header').text()).toBe(
                'PET phantom detector CLI');
            expect($('.g-execute-task-link .g-execute-task-link-body').text()).toContain(
                'Detects positions of PET/CT pocket phantoms in PET image.');
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
        expect($('input[name="MaximumRadius"]').val()).toBe('20');

        $('input[name="MaximumRadius"]').val('12').trigger('change');

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
            return $('.modal-dialog .g-folder-list-link:contains("tasks")').length > 0;
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
            return $('.modal-dialog .g-hierarchy-widget').length > 0;
        }, 'hierarchy widget to appear');

        runs(function () {
            // we should be in the parent folder selected before
            expect($('.modal-dialog a.g-breadcrumb-link').length).toBe(1);

            // go back to the user's main path
            $('.modal-dialog a.g-breadcrumb-link:first').click();

            // Select our user from the root selector
            var id = $('.modal-dialog #g-root-selector option:not([disabled]):first').attr('value');
            $('.modal-dialog #g-root-selector').val(id).trigger('change');
        });

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
            expect($('.g-input-value[input-id="--MaximumRadius"]').text()).toBe('12');
        });
    });

    it('Reconfigure task from previous execution details', function () {
        window.location.assign($('.g-item-task-setup-again a').attr('href'));

        waitsFor(function () {
            return $('input[name="MaximumRadius"]').val() === '12';
        }, 'task run view to display with same parameters');

        runs(function () {
            // Make sure item name displays properly
            expect($('input[name="InputImage"]').val()).toBe('PET phantom detector CLI');
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
            // loads specs.json
            $('.modal-dialog .g-configure-docker-image').val('me/my_image:latest');
            $('.modal-dialog button.btn.btn-success[type="submit"]').click();
        });

        waitsFor(function () {
            return $('.g-job-info-key').length > 0;
        }, 'navigation to the configuration job');

        waitsFor(function () {
            return $('.g-job-status-badge').attr('status') === 'success';
        }, 'job success status');
    });
});

describe('Navigate to the new JSON task', function () {
    it('navigate to task', function () {
        $('.g-nav-link[g-target="item_tasks"]').click();

        waitsFor(function () {
            return $('.g-execute-task-link').length > 0;
        }, 'task list to be rendered');

        runs(function () {
            expect($('.g-execute-task-link').length).toBe(3);
            expect($('.g-execute-task-link .g-execute-task-link-header').eq(0).text()).toBe(
                'me/my_image:latest 0');
            expect($('.g-execute-task-link .g-execute-task-link-header').eq(1).text()).toBe(
                'me/my_image:latest 1');
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

describe('Run task on item from item view', function () {
    it('navigate to collections', function () {
        runs(function () {
            $('ul.g-global-nav .g-nav-link[g-target="collections"]').click();
        });

        waitsFor(function () {
            return $('.g-collection-list-entry').length > 0;
        }, 'collection list to appear');
    });
    it('navigate to folders', function () {
        runs(function () {
            // Select the second collection, "task test"
            $('.g-collection-link:contains("task test")').click();
        });

        waitsFor(function () {
            return $('.g-folder-list-entry').length > 0;
        }, 'folder list to appear');
    });

    it('navigate to items', function () {
        runs(function() {
            $('.g-folder-list-link:contains("tasks")').click();
        });

        waitsFor(function () {
            return $('.g-item-list-entry').length > 0;
        }, 'item list to appear');
    });

    it('create item', function () {
        runs(function () {
            $('.g-folder-actions-menu .g-create-item').click();
        });

        girderTest.waitForDialog();

        runs(function () {
            $('.modal-dialog #g-name').val('Test input item');
            $('.modal-dialog .g-save-item').click();
        });

        waitsFor(function () {
            return $('.g-item-list-link:contains("Test input item")').length > 0;
        }, 'item to appear in the list');
    });

    it('select item', function () {
        runs(function () {
            $('.g-item-list-link:contains("Test input item")').click();
        });

        girderTest.waitForLoad();
    });

    it('run task on item from modal', function () {
        runs(function () {
            $('.g-item-actions-menu .g-select-item-task').click();
        });

        girderTest.waitForDialog();

        waitsFor(function () {
            return $('.g-list-group-item').length > 0;
        }, 'tasks to load in widget');

        runs(function () {
            $('.g-list-group-item.g-execute-task-link:contains("me/my_image:latest 1")').click();

            expect($('.g-selected-task-name').text()).toBe('me/my_image:latest 1');
            $('.g-submit-select-task').click();
        });

        girderTest.waitForLoad();

        runs(function () {
            // Expect to be on Run task page.
            expect($('.g-body-title').text()).toBe('Run task me/my_image:latest 1');
            // Expect file input field to be preselected to 'Test input item'.
            expect($('#testData').attr('value')).toBe('Test input item');
        });
    });
});

describe('Auto-configure the demo JSON task', function () {
    it('go to collection page', function () {
        $('ul.g-global-nav .g-nav-link[g-target="collections"]').click();
    });

    it('create collection and folder', girderTest.createCollection('demo task test', '', 'tasks'));

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
            return $('.g-item-list-link:contains("task placeholder")').length > 0;
        }, 'item to appear in the list');
    });

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
            $('.modal-dialog .g-configure-docker-image').val('item-tasks-demo');
            $('.modal-dialog .g-configure-task-name').val('item_tasks widget types demo');
            $('.modal-dialog button.btn.btn-success[type="submit"]').click();
        });

        waitsFor(function () {
            return $('.g-job-info-key').length > 0;
        }, 'navigation to the configuration job');

        waitsFor(function () {
            return $('.g-job-status-badge').attr('status') === 'success';
        }, 'job success status');
    });
});

describe('Navigate to the demo task', function () {
    it('navigate to task', function () {
        $('.g-nav-link[g-target="item_tasks"]').click();

        waitsFor(function () {
            return $('.g-execute-task-link').length > 0;
        }, 'task list to be rendered');

        runs(function () {
            expect($('.g-execute-task-link').length).toBe(4);
            expect($('.g-execute-task-link .g-execute-task-link-header').eq(0).text()).toBe(
                'item_tasks widget types demo');
            window.location.assign($('a.g-execute-task-link').eq(0).attr('href'));
        });

        waitsFor(function () {
            return $('.g-task-description-container').length > 0;
        }, 'task run view to display');

        runs(function () {
            expect($('.g-task-description-container').text()).toContain(
                'A simple demonstration showing how to work with item_tasks control widgets');
            expect($('.g-inputs-container').length).toBe(1);
            expect($('.g-outputs-container').length).toBe(1);
        });
    });

    it('task defaults', function () {
        expect($('#color_input').val()).toBe('#1234ef');
        expect($('#range_input').val()).toBe('5');
        expect($('#number_input').val()).toBe('0.5');
        expect($('#boolean_input').prop('checked')).toBe(true);
        expect($('#string_input').val()).toBe('default value');
        expect($('#integer_input').val()).toBe('3');
        expect($('#number_vector_input').val()).toBe('1,2,3');
        expect($('#string_vector_input').val()).toBe('one,two,three');
        expect($('#number_choice_input').val()).toBe('3.14');
        expect($('#string_choice_input').val()).toBe('green');
        expect($('#number_multi_choice_input').val()).toEqual(['3.14', '1.62']);
        expect($('#string_multi_choice_input').val()).toEqual(['green', 'yellow']);
        expect($('#file_input').val()).toBe('');
        expect($('#file_output').val()).toBe('');
    });

    it('set inputs and outputs', function () {
        runs(function () {
            $('#color_input').val('#b22222').trigger('change');
            $('#range_input').val('6').trigger('change');
            $('#number_input').val('1').trigger('change');
            $('#boolean_input').click();
            $('#string_input').val('another value').trigger('change');
            $('#integer_input').val('-4').trigger('change');
            $('#number_vector_input').val('-1,-2,-3').trigger('change');
            $('#string_vector_input').val('red,blue,green').trigger('change');
            $('#number_choice_input').val('1').trigger('change');
            $('#string_choice_input').val('cyan').trigger('change');
            $('#number_multi_choice_input').val(['3.14', '1.62']).trigger('change');
            $('#string_multi_choice_input').val(['green', 'blue']).trigger('change');
            $('#file_input').parent().find('button').click();
        });

        girderTest.waitForDialog();
        runs(function () {
            // Select our collection for the input item
            var id = $('.modal-dialog #g-root-selector option[data-group="Collections"]').attr('value');
            $('.modal-dialog #g-root-selector').val(id).trigger('change');
        });

        waitsFor(function () {
            return $('.modal-dialog .g-folder-list-link:contains("tasks")').length > 0;
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

        runs(function () {
            // set the output
            $('#file_output').parent().find('button').click();
        });

        girderTest.waitForDialog();

        runs(function () {
            $('#g-input-element').val('output.txt');
            $('.modal-dialog .g-submit-button').click();
        });

        waitsFor(function () {
            return $('#g-dialog-container').css('display') === 'none';
        }, 'modal dialog to disappear');
    });

    it('run the task', function () {
        runs(function () {
            $('.g-run-task').click();
        });

        waitsFor(function () {
            return $('.g-job-status-badge').attr('status') === 'success';
        }, 'job success status');

        waitsFor(function () {
            return $('.g-job-log-container').text();
        }, 'job log to appear');

        runs(function () {
            var args = JSON.parse($('.g-job-log-container').text());
            expect(args.color_input.data).toBe('#b22222');
            expect(args.range_input.data).toBe(6);
            expect(args.number_input.data).toBe(1);
            expect(args.boolean_input.data).toBe(false);
            expect(args.integer_input.data).toBe(-4);
            expect(args.number_vector_input.data).toBe('-1,-2,-3');
            expect(args.string_vector_input.data).toBe('red,blue,green');
            expect(args.number_choice_input.data).toBe(1);
            expect(args.string_choice_input.data).toBe('cyan');
            expect(args.number_multi_choice_input.data).toBe('3.14,1.62');
            expect(args.string_multi_choice_input.data).toBe('green,blue');
            expect(args.file_input.fileName).toBe('item_tasks widget types demo');
            expect(args.file_input.resource_type).toBe('item');
        });
    });
});

describe('Auto-configure the Slicer CLI item task folder', function () {
    it('go to collection page', function () {
        $('ul.g-global-nav .g-nav-link[g-target="collections"]').click();
    });

    it('create collection and folder', girderTest.createCollection('slicer cli task test', '', 'tasks'));

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
            $('.modal-dialog .g-configure-slicer-cli-task-tab > a').click();
            $('.modal-dialog .g-slicer-cli-docker-image').val('me/my_image:latest');
            $('.modal-dialog .g-slicer-cli-docker-args').val('["foo", "bar"]');
            $('.modal-dialog button.btn.btn-success[type="submit"]').click();
        });

        waitsFor(function () {
            return $('.g-job-info-key').length > 0;
        }, 'navigation to the configuration job');

        waitsFor(function () {
            return $('.g-job-status-badge').attr('status') === 'success';
        }, 'job success status');
    });
});

describe('Navigate to the new Slicer CLI task', function () {
    it('navigate to task', function () {
        $('.g-nav-link[g-target="item_tasks"]').click();

        waitsFor(function () {
            return $('.g-execute-task-link').length > 0;
        }, 'task list to be rendered');

        runs(function () {
            expect($('.g-execute-task-link').length).toBe(5);
            expect($('.g-execute-task-link .g-execute-task-link-header').eq(4).text()).toBe(
                'PET phantom detector CLI');
            expect($('.g-execute-task-link .g-execute-task-link-body').eq(4).text()).toContain(
                'Detects positions of PET/CT pocket phantoms in PET image.');
            window.location.assign($('a.g-execute-task-link').eq(4).attr('href'));
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
});
