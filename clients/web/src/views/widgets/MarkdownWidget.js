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
     * @param [settings.placeholder=''] Text area placeholder.
     * @param [settings.prefix='markdown'] Prefix for element IDs in case
     *     multiple of these widgets are rendered simultaneously.
     */
    initialize: function (settings) {
        this.text = settings.text || '';
        this.placeholder = settings.placeholder || '';
        this.prefix = settings.prefix || 'markdown';
    },

    render: function () {
        this.$el.html(girder.templates.markdownWidget({
            text: this.text,
            placeholder: this.placeholder,
            prefix: this.prefix
        }));
    },

    /**
     * Get or set the current markdown text. Call with no arguments to return
     * the current value, or call with one argument to set the value to that.
     */
    val: function () {
        if (arguments.length) {
            return this.$('.g-markdown-text').val(arguments[0]);
        } else {
            return this.$('.g-markdown-text').val();
        }
    }
});
