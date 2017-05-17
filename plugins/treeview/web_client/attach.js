import root from './root';

export default function (el, settings) {
    $(el).each(function () {
        settings = $.extend(true, {
            plugins: ['types'],
            core: {
                data: root(),
                force_text: true // prevent XSS
            },
            types: {
                folder: {
                    icon: 'icon-folder'
                },
                item: {
                    icon: 'icon-doc-text-inv'
                },
                user: {
                    icon: 'icon-user'
                },
                collection: {
                    icon: 'icon-globe'
                },
                users: {
                    icon: 'icon-users'
                },
                home: {
                    icon: 'icon-home'
                },
                collections: {
                    icon: 'icon-sitemap'
                },
                file: {
                    icon: 'icon-doc-inv'
                }
            }
        }, settings);
        $(this).jstree(settings);
    });
}
