import events from '../events';
import Panel from './Panel';
import JobsListWidget from './JobsListWidget';

const _ = girder._;

const JobsPanel = Panel.extend({
    events: _.extend(Panel.prototype.events, {
        'g:login': 'render',
        'g:login-changed': 'render',
        'g:logout': 'render'
    }),
    initialize(settings) {
        this.spec = settings.spec;
        this._jobsListWidget = new JobsListWidget({
            parentView: this
        });
        this.listenTo(events, 'h:submit', () => {
            this._jobsListWidget.collection.fetch(undefined, true);
        });
    },
    render() {
        Panel.prototype.render.apply(this, arguments);

        this._jobsListWidget.setElement(this.$('.s-panel-content')).render();
    }
});

export default JobsPanel;
