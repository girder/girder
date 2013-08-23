girder.models.UserModel = Backbone.Model.extend({
    name: function () {
        return this.get('firstName') + ' ' + this.get('lastName');
    },

    fetch: function () {
        girder.restRequest({
            path: 'user/' + this.get('_id'),
            error: null,
        }).done(_.bind(function (resp) {
            this.set(resp);
            this.trigger('g:fetched');
        }, this)).error(_.bind(function () {
            this.trigger('g:error');
        }, this));
    }
});
