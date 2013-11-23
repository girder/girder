/**
 * This widget is used to create a new collection or edit an existing one.
 */
girder.views.EditCollectionWidget = Backbone.View.extend({
    events: {
        'submit #g-collection-edit-form': function () {
            var fields = {
                name: this.$('#g-name').val(),
                description: this.$('#g-description').val()
            };

            if (this.collection) {
                this.collection.set('name', fields.name);
                this.collection.set('description', fields.description);
                this.updateCollection(fields);
            }
            else {
                this.createCollection(fields);
            }

            this.$('button.g-save-collection').addClass('disabled');
            this.$('.g-validation-failed-message').text('');

            return false;
        }
    },

    initialize: function (settings) {
        this.collection = settings.collection || null;
    },

    render: function () {
        var view = this;
        this.$el.html(
            jade.templates.editCollectionWidget(
                {'collection': view.collection}))
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-name').val(view.collection.get('name'));
                view.$('#g-description').val(view.collection.get('description'));
                view.$('#g-name').focus();
            });
        this.$('#g-name').focus();

        return this;
    },

    createCollection: function (fields) {
        girder.restRequest({
            path: 'collection',
            type: 'POST',
            data: fields,
            error: null // don't do default error behavior
        }).done(_.bind(function (resp) {
            this.$el.modal('hide');
            this.trigger('g:saved', resp);
        }, this)).error(_.bind(function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-collection').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this));
    },

    updateCollection: function (fields) {
        girder.restRequest({
            path: 'collection/' + this.collection.get('_id'),
            type: 'PUT',
            data: fields,
            error: null // don't do default error behavior
        }).done(_.bind(function (resp) {
            this.$el.modal('hide');
            this.trigger('g:saved', resp);
        }, this)).error(_.bind(function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-collection').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this));
    }
});
