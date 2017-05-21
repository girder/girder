import findResource from './findResource';

/**
 * Return a node in the tree instance from an id.  If the node is
 * not yet loaded into tree, it will query the server for the
 * resource resolving the path and loading it into the tree.
 *
 * On success, the returned promise will resolve with the node
 * object.  If the id is not found on the server, the promise
 * will be rejected.
 */
function getNode(jstree, id, type) {
    return new Promise((resolve, reject) => {
        let node = jstree.get_node(id);
        if (node) {
            resolve(node);
            return;
        }

        findResource(id, type).then((object) => {
            resolve(object);
        });
    });
}

export default getNode;
