/**
 * This widget is used to create a new API key or edit an existing one.
 */
girder.views.EditApiKeyWidget = girder.View.extend({
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

            this.$('button.g-save-api-key').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        },

        'change .g-scope-selection-container .radio input': function (e) {
            var mode = this._getSelectedScopeMode();
            if (mode === 'full') {
                this.$('.g-custom-scope-checkbox').attr('disabled', 'disabled');
            } else if (mode === 'custom') {
                this.$('.g-custom-scope-checkbox').removeAttr('disabled');
            }
        }
    },

    initialize: function (settings) {
        this.model = settings.model || null;
    },

    render: function () {
        var modal = this.$el.html(girder.templates.editApiKeyWidget({
            apiKey: this.model,
            user: girder.currentUser,
            userTokenScopes: girder.UserTokenScopes,
            adminTokenScopes: girder.AdminTokenScopes
        })).girderModal(this).on('shown.bs.modal', _.bind(function () {
            this.$('#g-api-key-name').focus();
        }, this)).on('ready.girder.modal', _.bind(function () {
            if (this.model) {
                this.$('#g-api-key-name').val(this.model.get('name'));
                this.$('#g-api-key-token-duration').val(this.model.get('tokenDuration') || '');
                if (this.model.get('scope')) {
                    this.$('#g-scope-mode-custom').attr('checked', 'checked');
                    this.$('.g-custom-scope-checkbox').removeAttr('disabled');
                    _.each(this.model.get('scope'), function (scope) {
                        this.$('.g-custom-scope-checkbox[value="' + scope + '"]').attr('checked', 'checked');
                    }, this);
                }
            }
        }, this));
        modal.trigger($.Event('ready.girder.modal', {relatedTarget: modal}));

        this.$('#g-api-key-name').focus();
        this.$('.g-custom-scope-description').tooltip({
            placement: 'right',
            viewport: this.$el,
            trigger: 'hover'
        });

        return this;
    },

    saveModel: function (model, fields) {
        model = model || new girder.models.ApiKeyModel();

        model.set(fields);
        model.once('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', model);
        }, this).off('g:error', null, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-api-key').removeClass('disabled');
        }, this).save();
    },

    _getSelectedScopeMode: function () {
        return this.$('.g-scope-selection-container .radio input:checked').attr('value');
    }
});
