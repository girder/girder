/* eslint underscore/jquery-each:off */
(function ($, d3) {
    'use strict';

    if (!($ && d3)) {
        return;
    }

    $.fn.girderBrowser = function (cfg) {
        var me,
            menu,
            item,
            caret,
            label,
            api,
            selectItem,
            selectFolder,
            selectSearchResult,
            findItems,
            findFolders,
            search,
            input,
            wait;

        // Extract cfg args.
        cfg = cfg || {};
        caret = cfg.caret === undefined ? 'true' : cfg.caret;
        label = (cfg.label || '') + (caret ? '<b class=caret></b>' : '');
        api = cfg.api || '/api/v1';
        selectItem = cfg.selectItem || $.noop;
        selectFolder = cfg.selectFolder || $.noop;
        selectSearchResult = cfg.selectSearchResult || $.noop;
        search = cfg.search;

        findItems = function (el, folderId) {
            var data;

            wait = el.append('li')
                .append('a')
                .text('Loading items...');

            data = {
                folderId: folderId
            };

            d3.json(api + '/item?' + $.param(data), function (error, items) {
                var anchor;

                if (error) {
                    throw new Error('[browser] could not retrieve items');
                }

                wait.remove();

                if (items.length > 0) {
                    $.each(items, function (i, item) {
                        anchor = el.append('li')
                            .append('a')
                            .attr('href', '#')
                            .text(item.name + ' (' + item.size + 'B)');

                        anchor.on('click', function () {
                            selectItem(item, api);
                        });
                    });
                }
            });
        };

        findFolders = function (el, parentType, parentId) {
            var data;

            el.append('li')
                .append('a')
                .text('Loading folders...');

            data = {
                parentType: parentType,
                parentId: parentId
            };
            d3.json(api + '/folder?' + $.param(data), function (error, folders) {
                var elem;

                if (error) {
                    throw new Error('[browser] could not retrieve folders');
                }

                $(el.node()).empty();

                $.each(folders, function (i, f) {
                    elem = el.append('li')
                        .classed('dropdown-submenu', true);

                    elem.append('a')
                        .attr('href', '#')
                        .text(f.name)
                        .on('click', function () {
                            selectFolder(f, api);
                        });

                    elem = elem.append('ul')
                        .classed('dropdown-menu', true);

                    findFolders(elem, 'folder', f._id);
                    elem.append('li')
                        .classed('divider', true);
                    findItems(elem, f._id);
                });
            });
        };

        // Empty the target element and make a d3 selection from it.
        $(this[0]).empty();
        me = d3.select(this[0]);

        // Class the target element as a dropdown.
        me.classed('dropdown', true);

        // Add an anchor tag with the label text.
        me.append('a')
            .attr('href', '#')
            .attr('role', 'button')
            .classed('dropdown-toggle', true)
            .attr('data-toggle', 'dropdown')
            .html(label);

        // Create the menu list.
        menu = me.append('ul')
            .classed('dropdown-menu', true);

        // If search mode is enabled, put in a text field.
        if (search) {
            input = menu.append('li')
                .append('input')
                .attr('type', 'text')
                .attr('placeholder', 'Quick search...');

            input.on('click', function () {
                d3.event.stopPropagation();
            })
                .on('keyup', (function () {
                    var xhr = null,
                        delayHandle = null,
                        doSearch;

                    doSearch = function (text, menu) {
                        var data;

                        if (xhr) {
                            xhr.abort();
                        }

                        if (text.length === 0) {
                            menu.selectAll('.search-result')
                                .remove();

                            return;
                        }

                        data = {
                            q: text,
                            types: JSON.stringify(['item'])
                        };

                        xhr = d3.json([api, 'resource', 'search'].join('/') + '?' + $.param(data), function (error, results) {
                            xhr = null;

                            if (error) {
                                throw new Error('[browser] could not perform search');
                            }

                            menu.selectAll('.search-result')
                                .remove();

                            if (results.item.length === 0) {
                                menu.append('li')
                                    .classed('search-result', true)
                                    .html('<em>No search results.</em>');
                            }

                            menu.selectAll('.search-result')
                                .data(results.item)
                                .enter()
                                .append('li')
                                .classed('search-result', true)
                                .append('a')
                                .attr('href', '#')
                                .text(function (d) {
                                    return d.name;
                                })
                                .on('click', function (d) {
                                    selectSearchResult(d, api);
                                });
                        });
                    };

                    return function () {
                        var text = d3.select(this).property('value');

                        window.clearTimeout(delayHandle);
                        delayHandle = window.setTimeout(doSearch, 200, text, menu);
                    };
                }()));
        }

        // Put down a placeholder 'item'.
        wait = menu.append('li')
            .append('a')
            .text('Loading...');

        // Query the Girder API for the top level users and collections, and
        // display them in the top menu level.
        d3.json(api + '/user', function (error, users) {
            if (error) {
                throw new Error('[browser] could not retrieve users');
            }

            wait.remove();

            if (users.length > 0) {
                menu.append('li')
                    .html('<strong>Users</strong>');

                $.each(users, function (i, user) {
                    item = menu.append('li')
                        .classed('dropdown-submenu', true);

                    item.append('a')
                        .attr('href', '#')
                        .text([user.firstName, user.lastName].join(' '));

                    item = item.append('ul')
                        .classed('dropdown-menu', true);

                    findFolders(item, 'user', user._id);
                });
            }

            d3.json(api + '/collection', function (error, collections) {
                if (error) {
                    throw new Error('[browser] could not retrieve collections');
                }

                if (collections.length > 0) {
                    menu.append('li')
                        .html('<strong>Collections</strong>');

                    $.each(collections, function (i, collection) {
                        item = menu.append('li')
                            .classed('dropdown-submenu', true);

                        item.append('a')
                            .attr('href', '#')
                            .text(collection.name);

                        item = item.append('ul')
                            .classed('dropdown-menu', true);

                        findFolders(item, 'collection', collection._id);
                    });
                }
            });
        });
        // Make the element into a Bootstrap dropdown.
        $(me.select('a').node()).dropdown();
    };
}(window.jQuery, window.d3));
