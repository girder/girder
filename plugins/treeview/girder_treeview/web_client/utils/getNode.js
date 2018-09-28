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
    let node = jstree.get_node(id);
    if (node) {
        return $.Deferred.resolve(node).promise();
    } else {
        return findResource(id, type);
    }
}

export default getNode;
