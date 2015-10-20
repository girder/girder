/**
 * A simple widget for editing markdown text with a preview tab.
 */
girder.views.MarkdownWidget = girder.View.extend({
    events: {
        'show.bs.tab .g-preview-link': function () {
            girder.renderMarkdown(this.val(), this.$('.g-markdown-preview'));
        }
    },

    /**
     * @param [settings.text=''] Initial markdown text.
     * @param [settings.prefix='markdown'] Prefix for element IDs in case
     *     multiple of these widgets are rendered simultaneously.
     */
    initialize: function (settings) {
        this.text = settings.text || '';
        this.prefix = settings.prefix || 'markdown';
    },

    render: function () {
        this.$el.html(girder.templates.markdownWidget({
            text: this.text,
            prefix: this.prefix
        }));
    },

    /**
     * Get the current markdown text from the widget.
     */
    val: function () {
        return this.$('.g-markdown-text').val();
    }
});
