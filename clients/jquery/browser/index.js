/*jslint browser: true */

/*globals $, d3 */

$(function () {
    "use strict";

    var selectItem = function (item, api) {
        var div = d3.select("#file-info"),
            link;

        div.selectAll("*")
            .remove();

        div.append("p")
            .html("<b>Name:</b> " + item.name);

        div.append("p")
            .html("<b>Created:</b> " + item.created);

        div.append("p")
            .html("<b>Updated:</b> " + item.updated);

        div.append("p")
            .html("<b>Size:</b> " + item.size);

        link = [api, "item", item._id, "download"].join("/");
        div.append("p")
            .html("<a href=" + link + ">Download</a>");
    };

    $("#girder-browser").girderBrowser({
        label: "Girder",
        search: true,
        selectItem: selectItem,
        selectSearchResult: function (item, api) {
            d3.json([api, "item", item._id].join("/"), function (error, itemInfo) {
                if (error) {
                    throw new Error("[browser] could not load item info for " + item._id);
                }

                selectItem(itemInfo, api);
            });
        },
        selectFolder: function (folder, api) {
            var div = d3.select("#file-info"),
                link;

            div.selectAll("*")
                .remove();

            div.append("p")
                .html("<b>Name:</b> " + folder.name);

            div.append("p")
                .html("<b>Created:</b> " + folder.created);

            div.append("p")
                .html("<b>Updated:</b> " + folder.updated);

            div.append("p")
                .html("<b>Size:</b> " + folder.size);

            div.append("p")
                .html("<b>Description:</b> " + folder.description);

            link = [api, "folder", folder._id, "download"].join("/");
            div.append("p")
                .html("<a href=" + link + ">Download</a>");
        }
    });
});
