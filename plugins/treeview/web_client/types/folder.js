export default function (folder) {
    return {
        id: folder._id,
        parent: folder.parentId,
        type: 'folder',
        text: folder.name,
        model: folder,
        children: true
    };
}
