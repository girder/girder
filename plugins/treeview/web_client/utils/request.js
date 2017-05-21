import { restRequest } from 'girder/rest';

function rest() {
    // Add a hook for unit testing without communicating with the server.
    if (window.girderTreeViewRest) {
        return window.girderTreeViewRest.apply(this, arguments);
    }
    return restRequest.apply(this, arguments);
}

export default rest;
