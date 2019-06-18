import $ from 'jquery';

import { AccessType } from '@girder/core/constants';
import EditCollectionWidget from '@girder/core/views/widgets/EditCollectionWidget';
import MarkdownWidget from '@girder/core/views/widgets/MarkdownWidget';
import { wrap } from '@girder/core/utilities/PluginUtils';

import EditCollectionTermsWidgetTemplate from '../templates/editCollectionTermsWidget.pug';
import '../stylesheets/editCollectionTermsWidget.styl';

wrap(EditCollectionWidget, 'initialize', function (initialize, ...args) {
    initialize.apply(this, args);

    // Only render if creating a new collection or editing one with admin
    if (this.create || this.model.getAccessLevel() >= AccessType.ADMIN) {
        this.termsEditor = new MarkdownWidget({
            text: this.model ? this.model.get('terms') : '',
            prefix: 'collection-terms',
            placeholder: 'Enter collection Terms of Use',
            enableUploads: false,
            parentView: this
        });
    }
});

wrap(EditCollectionWidget, 'render', function (render) {
    render.call(this);

    if (this.termsEditor) {
        const newEl = $(EditCollectionTermsWidgetTemplate({
            enabled: true
        }));
        this.termsEditor
            .setElement(newEl.find('.g-terms-editor-container'))
            .render();

        this.$('.modal-body>.g-validation-failed-message').before(newEl);
    }

    return this;
});

wrap(EditCollectionWidget, '_saveCollection', function (_saveCollection, fields) {
    if (this.termsEditor) {
        fields.terms = this.termsEditor.val();
        // Don't call though to _saveCollection, since we want the current user to accept the terms
        // before 'g:saved' gets triggered on EditCollectionWidget (which causes routing when a
        // new collection is created).
        this.model.set(fields);
        return this.model.save()
            .then(() => {
                if (this.model.hasTerms()) {
                    // Any user that can successfully set the terms should be considered to have
                    // accepted them
                    return this.model.currentUserSetAcceptTerms();
                } else {
                    return undefined;
                }
            })
            .done(() => {
                this.trigger('g:saved', this.model);
            });
    } else {
        return _saveCollection.call(this, fields);
    }
});
