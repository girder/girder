export default function (collection) {
    return {
        id: collection._id,
        parent: '#collections',
        type: 'collection',
        text: collection.name,
        model: collection,
        children: true
    };
}
