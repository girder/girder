<!DOCTYPE html>
<html lang="en">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${brandName | h}</title>
    <link rel="stylesheet" href="${staticPublicPath}/built/girder_lib.min.css">
    <link rel="icon" type="image/png" href="${staticPublicPath}/built/Girder_Favicon.png">
    % for plugin in pluginCss:
    <link rel="stylesheet" href="${staticPublicPath}/built/plugins/${plugin}/plugin.min.css">
    <link rel="stylesheet" href="${staticPublicPath}/built/extras/extra.css">
    % endfor
    <!-- TODO: In Girder 5 install tailwind the right way -->
    <script src="https://cdn.tailwindcss.com"></script>

    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            DEFAULT: 'hsl(var(--primary-h), var(--primary-s), var(--primary-l))',
                            hover: 'var(--primary-hover)',
                            content: 'var(--primary-content)',
                        },
                        secondary: {
                            DEFAULT: 'hsl(var(--secondary-h), var(--secondary-s), var(--secondary-l))',
                            hover: 'var(--secondary-hover)',
                            content: 'var(--secondary-content)',
                        },
                        accent: {
                            DEFAULT: 'hsl(var(--accent-h), var(--accent-s), var(--accent-l))',
                            hover: 'var(--accent-hover)',
                            content: 'var(--accent-content)',
                        },
                    },
                    zIndex: {
                        '100': '100',
                    },
                },
            },
            plugins: [],
            blocklist: ['collapse'], // disable because bootstrap uses it for something else
        };
    </script>

<style type="text/tailwindcss">
    @layer base {
        :root {
            /* User-defined hex values */
            --primary: ${bannerColor};
            --secondary: ${bannerColor};
            --accent: ${bannerColor};
        }

        body {
            @apply bg-zinc-100;
        }

        /* Typography Styles */
        h1,
        h2,
        h3,
        h4,
        h5,
        h6 {
            @apply font-bold;
        }

        h1 {
            @apply text-4xl;
        }

        h2 {
            @apply text-3xl;
        }

        h3 {
            @apply text-2xl;
        }

        h4 {
            @apply text-xl;
        }

        h5 {
            @apply text-lg;
        }

        h6 {
            @apply text-base;
        }
    }

    @layer components {

        /*
        Define button styles:
            1. Sizes
            2. Colors
            3. Types
        */

        .htk-btn {
            @apply duration-200 ease-in-out inline-flex items-center justify-center px-3 py-[6px] rounded-md text-base tracking-wider transition-all gap-2 h-9;
        }

        .htk-btn i {
            @apply leading-[0];
        }

        /* 1. Sizes */

        .htk-btn.htk-btn-lg {
            @apply px-4 text-lg h-11;
        }

        .htk-btn.htk-btn-sm {
            @apply px-[10px] text-sm h-[30px] gap-1;
        }

        .htk-btn.htk-btn-xs {
            @apply px-[7px] rounded text-xs h-[22px] gap-1;
        }

        /* 2. Colors */

        .htk-btn.htk-btn-primary {
            @apply bg-primary text-primary-content;
        }

        .htk-btn.htk-btn-primary:hover {
            @apply bg-primary-hover;
        }

        .htk-btn.htk-btn-secondary {
            @apply bg-secondary text-secondary-content;
        }

        .htk-btn.htk-btn-secondary:hover {
            @apply bg-secondary-hover;
        }

        .htk-btn.htk-btn-accent {
            @apply bg-accent text-accent-content;
        }

        .htk-btn.htk-btn-accent:hover {
            @apply bg-accent-hover;
        }

        /* 3. Types
                a. Ghost
                b. Icon Only
                c. Disabled
        */

        /* a. Ghost */

        .htk-btn.htk-btn-ghost {
            @apply bg-neutral-800 bg-opacity-0;
        }

        .htk-btn.htk-btn-ghost:hover {
            @apply bg-opacity-10;
        }

        /* Primary Color */

        .htk-btn.htk-btn-primary.htk-btn-ghost {
            background-color: hsla(var(--primary-h), var(--primary-s), var(--primary-l), 0);
            @apply text-primary;
        }
        .htk-btn.htk-btn-primary.htk-btn-ghost:hover {
            background-color: hsla(var(--primary-h), var(--primary-s), var(--primary-l), 0.1);
        }

        /* Secondary Color */

        .htk-btn.htk-btn-secondary.htk-btn-ghost {
            background-color: hsla(var(--secondary-h), var(--secondary-s), var(--secondary-l), 0);
            @apply text-secondary;
        }
        .htk-btn.htk-btn-secondary.htk-btn-ghost:hover {
            background-color: hsla(var(--secondary-h), var(--secondary-s), var(--secondary-l), 0.1);
        }

        /* Accent Color */

        .htk-btn.htk-btn-accent.htk-btn-ghost {
            background-color: hsla(var(--accent-h), var(--accent-s), var(--accent-l), 0);
            @apply text-accent;
        }
        .htk-btn.htk-btn-accent.htk-btn-ghost:hover {
            background-color: hsla(var(--accent-h), var(--accent-s), var(--accent-l), 0.1);
        }

        /* b. Icon Only */

        .htk-btn.htk-btn-icon {
            /* "tracking-[0]" ensures icons are always centered when using icon fonts */
            @apply rounded-full !leading-none text-xl w-9 aspect-square tracking-[0];
        }

        /* Large */

        .htk-btn.htk-btn-icon.htk-btn-lg {
            @apply text-2xl w-11;
        }

        /* Small */

        .htk-btn.htk-btn-icon.htk-btn-sm {
            @apply text-lg w-[30px];
        }

        /* X-Small */

        .htk-btn.htk-btn-icon.htk-btn-xs {
            @apply text-sm w-[22px];
        }

        /* c. Disabled */
        .htk-btn.htk-btn-disabled {
            @apply bg-neutral-200 border border-neutral-300 text-neutral-400 !cursor-not-allowed;
        }

        /* Use this instead of Tailwind's hidden until we remove bootstrap */
        /* Required for now to account for the fact that bootstrap has !important on .hidden */
        .htk-hidden {
            display: none;
        }
    }
</style>


  </head>
  <body>
    <div id="g-global-info-apiroot" class="hide">${apiRoot}</div>
    <script src="${staticPublicPath}/built/girder_lib.min.js"></script>
    <script src="${staticPublicPath}/built/girder_app.min.js"></script>
    <script type="text/javascript">
        $(function () {
            girder.events.trigger('g:appload.before');
            girder.app = new girder.views.App({
                el: 'body',
                parentView: null,
                contactEmail: '${contactEmail | js}',
                privacyNoticeHref: '${privacyNoticeHref | js}',
                brandName: '${brandName | js}',
                bannerColor: '${bannerColor | js}',
                registrationPolicy: '${registrationPolicy | js}',
                enablePasswordLogin: ${enablePasswordLogin | n,json,js}
            }).render();
            girder.events.trigger('g:appload.after', girder.app);
        });
    </script>
    % for plugin in pluginJs:
    <script src="${staticPublicPath}/built/plugins/${plugin}/plugin.min.js"></script>
    % endfor


<%text>
<script type="text/javascript">
    function hexToHSL(hex) {
        let r = 0, g = 0, b = 0;
        if (hex.length === 4) {
            r = parseInt(hex[1] + hex[1], 16);
            g = parseInt(hex[2] + hex[2], 16);
            b = parseInt(hex[3] + hex[3], 16);
        } else if (hex.length === 7) {
            r = parseInt(hex[1] + hex[2], 16);
            g = parseInt(hex[3] + hex[4], 16);
            b = parseInt(hex[5] + hex[6], 16);
        }
        r /= 255;
        g /= 255;
        b /= 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        let h = 0, s = 0, l = (max + min) / 2;
        if (max !== min) {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        s = s * 100;
        l = l * 100;
        h = Math.round(h * 360);
        s = Math.round(s);
        l = Math.round(l);
        return { h, s, l };
    }

    function setColorVariables(hexVar, prefix) {
        const hex = getComputedStyle(document.documentElement).getPropertyValue(hexVar).trim();
        const { h, s, l } = hexToHSL(hex);

        const styles = `
            --${prefix}-h: ${h};
            --${prefix}-s: ${s}%;
            --${prefix}-l: ${l}%;
            --${prefix}-hover: hsl(${h}, ${s}%, ${l + (l > 50 ? -10 : 10)}%);
            --${prefix}-content: hsl(${h}, ${s}%, ${l > 50 ? l - 60 : l + 60}%);
        `;
        return styles;
    }

    function injectStyles() {
        const primaryStyles = setColorVariables('--primary', 'primary');
        const secondaryStyles = setColorVariables('--secondary', 'secondary');
        const accentStyles = setColorVariables('--accent', 'accent');

        let styleElement = document.getElementById('dynamic-color-styles');

        if (!styleElement) {
            styleElement = document.createElement('style');
            styleElement.id = 'dynamic-color-styles';
            document.head.appendChild(styleElement);
        }

        styleElement.textContent = `:root { ${primaryStyles} ${secondaryStyles} ${accentStyles} }`;
    }

    injectStyles();
</script>
</%text>


  </body>
</html>
