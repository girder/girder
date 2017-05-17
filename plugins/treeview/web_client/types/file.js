export default function (file) {
    return {
        id: file._id,
        parent: file.itemId,
        type: 'file',
        text: file.name,
        model: file
    };
}
