import AssetstoreModel from '@girder/core/models/AssetstoreModel';
import View from '@girder/core/views/View';
import { AssetstoreType } from '@girder/core/constants';

import router from '@girder/core/router';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

const goBack = (assetstoreId, message) => {
    events.trigger('g:alert', {
        icon: 'cancel',
        text: `Could not re-import: ${message}`,
        type: 'danger'
    });
    router.navigate(
        `assetstore/${assetstoreId}/import`,
        { trigger: true, replace: true }
    );
};

var reImportView = View.extend({
    initialize({ assetstoreId, importId }) {
        this.importId = importId;
        this.assetstoreId = assetstoreId;
        this.type = '';

        restRequest({
            url: `assetstore/import/${importId}`,
            error: null
        }).done((assetstoreImport) => {
            if (!assetstoreImport) {
                goBack(this.assetstoreId, `Unable to find import ${importId}`);
                return;
            }

            this.import = assetstoreImport;

            // collect assetstore type info and render
            const assetstore = new AssetstoreModel({ _id: assetstoreId });
            assetstore.once('g:fetched', () => {
                const assetstoreType = assetstore.get('type');
                if (assetstoreType === AssetstoreType.FILESYSTEM) {
                    this.type = 'filesystem';
                } else if (assetstoreType === AssetstoreType.S3) {
                    this.type = 's3';
                } else if (assetstoreType === AssetstoreType.DICOMWEB) {
                    this.type = 'dwas';
                } else if (assetstoreType === AssetstoreType.GIRDER) {
                    this.type = 'gas';
                } else {
                    goBack(this.assetstoreId, `Unsupported assetstore type '${assetstoreType}'`);
                }
                this.render();
            }).fetch();
        }).fail(() => {
            goBack(this.assetstoreId, 'Unable to fetch base import information');
        });
    },

    render() {
        const params = this.import.params;
        const destId = params.destinationId;
        const destType = params.destinationType;
        const excludeExisting = params.excludeExisting ? 'true' : 'false';

        this.$(`#g-${this.type}-import-path`).val(params.importPath);
        this.$(`#g-${this.type}-import-dest-type`).val(destType);
        this.$(`#g-${this.type}-import-dest-id`).val(destId);
        this.$(`#g-${this.type}-import-leaf-items`).val(params.leafFoldersAsItems);
        this.$(`#g-${this.type}-import-exclude-existing`).val(excludeExisting);

        if (this.type === 'dwas') {
            this.$(`#g-${this.type}-import-filters`).val(params.filters);
            this.$(`#g-${this.type}-import-limit`).val(params.limit);
        }

        restRequest({
            url: `resource/${destId}/path`,
            method: 'GET',
            data: { type: destType },
            error: null
        }).done((path) => {
            this.$(`#g-${this.type}-import-dest-id`).val(`${destId} (${path})`);
        }).fail(() => {
            this.$(`#g-${this.type}-import-dest-id`).val('');
        });

        return this;
    }
});

export default reImportView;
