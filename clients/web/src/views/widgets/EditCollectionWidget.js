/**
 * This widget is used to create a new collection or edit an existing one.
 */
girder.views.EditCollectionWidget = Backbone.View.extend({
    events: {
        'submit #g-collection-edit-form': function (e) {
            e.preventDefault();

            var fields = {
                name: this.$('#g-name').val(),
                description: this.$('#g-description').val()
            };

            if (this.model) {
                this.model.set('name', fields.name);
                this.model.set('description', fields.description);
                this.updateCollection(fields);
            }
            else {
                this.createCollection(fields);
            }

            this.$('button.g-save-collection').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        }
    },

    initialize: function (settings) {
        this.model = settings.model || null;
    },

    render: function () {
        var view = this;
        this.$el.html(jade.templates.editCollectionWidget({
            collection: view.model
        })).girderModal(this).on('shown.bs.modal', function () {
            if (view.model) {
                view.$('#g-name').val(view.model.get('name'));
                view.$('#g-description').val(view.model.get('description'));
            }
            view.$('#g-name').focus();
        });
        this.$('#g-name').focus();

        return this;
    },

    createCollection: function (fields) {
        var collection = new girder.models.CollectionModel();
        collection.set(fields);
        collection.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', collection);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-collection').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },

    updateCollection: function (fields) {
        this.model.set(fields);
        this.model.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.model);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-collection').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    }
});
