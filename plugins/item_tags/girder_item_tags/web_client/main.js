import './routes';
import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';
import './views/MetadataWidget';

SearchFieldWidget.addMode(
    'item_tags',
    ['item'],
    'Item tag search',
    `You are searching by item tag. Only items manually tagged with all of the search keywords
        will be returned.`
);
