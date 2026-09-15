/**
 * Given a view, returns whether or not the download widget(s)
 * should be displayed to the user.
 *
 * @param {Backbone.View} view
 * @returns the value of the SHOW_DOWNLOAD setting in the current
 * view hierarchy. Defaults to `true`.
 */
export function showDownload(view) {
    let baseView = view;
    while (baseView.parentView) {
        baseView = baseView.parentView;
    }
    return baseView && baseView.showDownload ? baseView.showDownload() : true;
}
