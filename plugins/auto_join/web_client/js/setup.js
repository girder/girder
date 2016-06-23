girder.views.AutoJoinWidget = girder.View.extend({
    initialize: function (settings) {
        this.group = settings.group;
        this.group.on('g:changed', function () {
            this.render();
        }, this);
        this.render();
    },
    render: function () {
        this.$el.html(girder.templates.auto_join_container({
            group: this.group
        }));
        return this;
    }
});

girder.wrap(girder.views.GroupView, 'render', function (render) {
    // render parent
    render.call(this);

    // add auto join tab
    var tab = $('<li></li>').html(girder.templates.auto_join_tab());
    $('.g-group-tabs').append(tab);

    // add auto join widget
    var el = $('<div id="g-group-tab-auto-join" class="tab-pane"></div>');
    $('.tab-content').append(el);

    new girder.views.AutoJoinWidget({
        el: el,
        group: this.model,
        parentView: this
    });

    // update window location when the tab is clicked
    var tabLink = $('a[href="#g-group-tab-auto-join"]');
    tabLink.tab().on('shown.bs.tab', function (e) {
        this.tab = $(e.currentTarget).attr('name');
        girder.router.navigate('group/' + this.model.get('_id') + '/' + this.tab);
    }.bind(this));

    if (tabLink.attr('name') === this.tab) {
        tabLink.tab('show');
    }

    return this;
});
