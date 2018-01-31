import $ from 'jquery';
import moment from 'moment';

import View from 'girder/views/View';
import events from 'girder/events';
import { getCurrentUser } from 'girder/auth';
import { restRequest } from 'girder/rest';

import CurationDialogTemplate from '../templates/curationDialog.pug';
import '../stylesheets/curationDialog.styl';

import 'girder/utilities/jquery/girderModal';

var CurationDialog = View.extend({
    events: {
        'click #g-curation-enable': function (event) {
            event.preventDefault();
            this._save('Enabled folder curation', {
                id: this.folder.get('_id'),
                enabled: true
            });
        },
        'click #g-curation-disable': function (event) {
            event.preventDefault();
            this._save('Disabled folder curation', {
                id: this.folder.get('_id'),
                enabled: false
            });
        },
        'click #g-curation-request': function (event) {
            event.preventDefault();
            this._save('Submitted folder for admin approval', {
                id: this.folder.get('_id'),
                status: 'requested'
            });
        },
        'click #g-curation-approve': function (event) {
            event.preventDefault();
            this._save('Approved curated folder', {
                id: this.folder.get('_id'),
                status: 'approved'
            });
        },
        'click #g-curation-reject': function (event) {
            event.preventDefault();
            this._save('Rejected curated folder', {
                id: this.folder.get('_id'),
                status: 'construction'
            });
        },
        'click #g-curation-reopen': function (event) {
            event.preventDefault();
            this._save('Reopened curated folder', {
                id: this.folder.get('_id'),
                status: 'construction'
            });
        }
    },

    initialize: function (settings) {
        this.folder = this.parentView.parentModel;
        this.curation = {timeline: []};
        restRequest({
            url: `folder/${this.folder.id}/curation`
        }).done((resp) => {
            this.curation = resp;
            this.render();
        });
    },

    render: function (refresh) {
        var q = this.$el.html(CurationDialogTemplate({
            folder: this.folder,
            curation: this.curation,
            moment: moment
        }));

        if (!refresh) {
            q.girderModal(this);
        }

        // show only relevant action buttons
        $('.g-curation-action-container button').hide();
        if (this.curation.enabled) {
            if (this.curation.status === 'construction') {
                $('#g-curation-request').show();
            }
            if (getCurrentUser().get('admin')) {
                $('#g-curation-disable').show();
                if (this.curation.status === 'requested') {
                    $('#g-curation-approve').show();
                    $('#g-curation-reject').show();
                }
                if (this.curation.status === 'approved') {
                    $('#g-curation-reopen').show();
                }
            }
        } else {
            if (getCurrentUser().get('admin')) {
                $('#g-curation-enable').show();
            }
        }

        return this;
    },

    _save: function (successText, data) {
        restRequest({
            method: 'PUT',
            url: `folder/${this.folder.id}/curation`,
            data: data
        }).done((resp) => {
            this.curation = resp;
            this.render(true);
            events.trigger('g:alert', {
                icon: 'ok',
                text: successText,
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-curation-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default CurationDialog;
