export default function (item) {
    return {
        id: item._id,
        parent: item.folderId,
        type: 'item',
        text: item.name,
        model: item,
        children: true
    };
}
