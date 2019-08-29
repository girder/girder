import $ from 'jquery';
import _ from 'underscore';

import ApiKeyModel from '@girder/core/models/ApiKeyModel';
import View from '@girder/core/views/View';
import { getCurrentUser } from '@girder/core/auth';
import { restRequest } from '@girder/core/rest';

import EditApiKeyWidgetTemplate from '@girder/core/templates/widgets/editApiKeyWidget.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This widget is used to create a new API key or edit an existing one.
 */
var EditApiKeyWidget = View.extend({
    events: {
        'submit #g-api-key-edit-form': function (e) {
            e.preventDefault();

            var fields = {
                name: this.$('#g-api-key-name').val(),
                tokenDuration: this.$('#g-api-key-token-duration').val(),
                scope: null
            };

            if (this._getSelectedScopeMode() === 'custom') {
                fields.scope = _.map(this.$('.g-custom-scope-checkbox:checked'), function (el) {
                    return $(el).val();
                });
            }

            this.saveModel(this.model, fields);

            this.$('button.g-save-api-key').girderEnable(false);
            this.$('.g-validation-failed-message').text('');
        },

        'change .g-scope-selection-container .radio input': function () {
            var mode = this._getSelectedScopeMode();
            if (mode === 'full') {
                this.$('.g-custom-scope-checkbox').girderEnable(false)
                    .parent().parent().girderEnable(false);
            } else if (mode === 'custom') {
                this.$('.g-custom-scope-checkbox').girderEnable(true)
                    .parent().parent().girderEnable(true);
            }
        }
    },

    initialize: function (settings) {
        this.model = settings.model || null;
        this.scopeInfo = null;
        this._shouldRender = false;

        restRequest({
            url: 'token/scopes'
        }).done((resp) => {
            this.scopeInfo = resp;
            if (this._shouldRender) {
                this._shouldRender = false;
                this.render();
            }
        });
    },

    render: function () {
        if (!this.scopeInfo) { // Wait for scope list to be fetched
            this._shouldRender = true;
            return;
        }

        let tokenScopes = this.scopeInfo.custom;
        if (getCurrentUser().get('admin')) {
            tokenScopes = tokenScopes.concat(this.scopeInfo.adminCustom);
        }

        var modal = this.$el.html(EditApiKeyWidgetTemplate({
            apiKey: this.model,
            tokenScopes: tokenScopes
        })).girderModal(this).on('shown.bs.modal', () => {
            this.$('#g-api-key-name').focus();
        }).on('ready.girder.modal', () => {
            if (this.model) {
                this.$('#g-api-key-name').val(this.model.get('name'));
                this.$('#g-api-key-token-duration').val(this.model.get('tokenDuration') || '');
                if (this.model.get('scope')) {
                    this.$('#g-scope-mode-custom').attr('checked', 'checked').trigger('change');
                    this.$('.g-custom-scope-checkbox').girderEnable(true);
                    _.each(this.model.get('scope'), function (scope) {
                        this.$('.g-custom-scope-checkbox[value="' + scope + '"]').attr('checked', 'checked');
                    }, this);
                }
            }
        });
        modal.trigger($.Event('ready.girder.modal', { relatedTarget: modal }));

        this.$('#g-api-key-name').focus();

        return this;
    },

    saveModel: function (model, fields) {
        model = model || new ApiKeyModel();

        model.set(fields);
        model.once('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', model);
        }, this).off('g:error', null, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-api-key').girderEnable(true);
        }, this).save();
    },

    _getSelectedScopeMode: function () {
        return this.$('.g-scope-selection-container .radio input:checked').attr('value');
    }
});

export default EditApiKeyWidget;
