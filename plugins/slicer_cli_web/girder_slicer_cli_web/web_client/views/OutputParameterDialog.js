import outputParameterDialog from '../templates/outputParameterDialog.pug';
import '../stylesheets/outputParameterDialog.styl';

const View = girder.views.View;

const OutputParameterDialog = View.extend({
    initialize(settings) {
        this.parameters = settings.parameters;
    },

    render() {
        this.$el.html(
            outputParameterDialog({
                parameters: this.parameters
            })
        ).girderModal(this);
        return this;
    }
});

export default OutputParameterDialog;
