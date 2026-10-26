import $ from 'jquery';
import _ from 'underscore';

import htkStylesheetUrl from '@girder/core/stylesheets/htk/htk.css?url';

/**
 * The web client can render with one of two looks:
 *
 *   - "classic": the long-standing Girder look.
 *   - "htk": a Tailwind-based restyle of the header, hierarchy widget and
 *     related widgets.
 *
 * The look is chosen by the core.ui_style setting and applied when the
 * application starts. Views pick templates and behaviours through the helpers
 * in this module; stylesheets scope style-specific rules with the "g-ui-htk"
 * class that setUiStyle places on the document element.
 */
const UI_STYLES = ['classic', 'htk'];
const HTK_CLASS = 'g-ui-htk';

let uiStyle = 'classic';
let htkStylesheetPromise = null;

/**
 * Get the current UI style, either "classic" or "htk".
 */
function getUiStyle() {
    return uiStyle;
}

/**
 * Whether the "htk" UI style is active.
 */
function isHtkStyle() {
    return uiStyle === 'htk';
}

/**
 * Load the htk stylesheet. It is placed after the core stylesheets (so that
 * it takes precedence over bootstrap and the core styles where they conflict,
 * Tailwind's preflight reset in particular) and before any plugin stylesheets,
 * which is the order the stylesheet was written against.
 *
 * @returns {$.Promise} Resolves once the stylesheet has loaded. A stylesheet
 *     that fails to load also resolves, so the application still starts.
 */
function loadHtkStylesheet() {
    if (!htkStylesheetPromise) {
        const deferred = $.Deferred();
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = htkStylesheetUrl;
        link.setAttribute('data-g-ui-style', 'htk');
        link.addEventListener('load', () => deferred.resolve());
        link.addEventListener('error', () => {
            console.error('Could not load the htk stylesheet.');
            deferred.resolve();
        });
        document.head.insertBefore(link, document.head.querySelector('link[data-g-plugin-stylesheet]'));
        htkStylesheetPromise = deferred.promise();
    }
    return htkStylesheetPromise;
}

/**
 * Set the UI style. Unknown values fall back to "classic".
 *
 * @param {string} style Either "classic" or "htk".
 * @returns {$.Promise} Resolves when any stylesheet the style needs is loaded.
 */
function setUiStyle(style) {
    uiStyle = _.contains(UI_STYLES, style) ? style : 'classic';
    document.documentElement.classList.toggle(HTK_CLASS, uiStyle === 'htk');
    if (uiStyle === 'htk') {
        return loadHtkStylesheet();
    }
    return $.Deferred().resolve().promise();
}

/**
 * Combine a classic and an htk template into one template function that
 * renders whichever matches the current UI style.
 *
 * @param {function} classicTemplate The compiled template for the classic style.
 * @param {function} htkTemplate The compiled template for the htk style.
 * @returns {function} A template function taking the same locals.
 */
function styledTemplate(classicTemplate, htkTemplate) {
    return (locals) => (isHtkStyle() ? htkTemplate : classicTemplate)(locals);
}

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

/**
 * Derive the htk style's theme colors from the banner color.
 *
 * The banner color is published as the --primary, --secondary and --accent
 * custom properties in the "base" cascade layer, so a deployment's extra
 * stylesheet can override them. The HSL components and the hover and content
 * variants that the htk stylesheet uses are then computed from whichever
 * values end up applying.
 *
 * @param {string} bannerColor The banner color as a hex string.
 */
function applyHtkBannerColor(bannerColor) {
    const css = `@layer base {
        :root {
          --primary: ${bannerColor};
          --secondary: ${bannerColor};
          --accent: ${bannerColor};
        }
    }`;
    const style = document.createElement('style');
    style.appendChild(document.createTextNode(css));
    document.head.insertBefore(style, document.head.firstChild);

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

export {
    UI_STYLES,
    applyHtkBannerColor,
    getUiStyle,
    isHtkStyle,
    setUiStyle,
    styledTemplate
};
