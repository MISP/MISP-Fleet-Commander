<template>
    <div v-html="getHtml"></div>
</template>

<script>
// Plugin-supplied HTML is untrusted: only render an allow-list of formatting
// elements and attributes, everything else is dropped.
const ALLOWED_TAGS = new Set([
    'a', 'abbr', 'b', 'blockquote', 'br', 'caption', 'code', 'dd', 'div', 'dl', 'dt',
    'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'li', 'ol', 'p', 'pre',
    'small', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
    'thead', 'tr', 'u', 'ul', 'iframe', 'img',
])
// `class` is deliberately not allowed: bootstrap.css is loaded globally (see
// web/src/main.js), so a kept class would let plugin HTML address the whole
// application class namespace, including positioned overlay classes.
const ALLOWED_ATTRIBUTES = new Set(['title', 'colspan', 'rowspan', 'style'])
// Embedding is kept for plugins rendering a remote dashboard (see GrafanaPanel),
// restricted to a fixed set of attributes and to http(s) sources.
const ALLOWED_TAG_ATTRIBUTES = {
    a: new Set(['href']),
    iframe: new Set(['src', 'width', 'height', 'frameborder']),
    img: new Set(['src', 'alt', 'width', 'height']),
}
const URL_ATTRIBUTES = { a: 'href', iframe: 'src', img: 'src' }
const ALLOWED_URL_PROTOCOLS = { a: ['http:', 'https:', 'mailto:'], iframe: ['http:', 'https:'], img: ['http:', 'https:'] }
// Only geometry properties survive. A transform may only shrink, and its origin
// is restricted to keywords and in-box percentages, so the displacement a
// transform can introduce stays within the element's own box.
const ALLOWED_STYLE_PROPERTIES = new Set([
    'width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
    'transform', 'transform-origin', 'background-color',
])
const ALLOWED_TRANSFORM = /^scale\((0(\.\d+)?|1)(, ?(0(\.\d+)?|1))?\)$/
const TRANSFORM_ORIGIN_POSITION = '(left|right|center|top|bottom|(100|\\d{1,2}(\\.\\d+)?)%)'
// Firefox serializes the origin with an explicit zero z-offset ("left top 0px").
const ALLOWED_TRANSFORM_ORIGIN = new RegExp(
    `^${TRANSFORM_ORIGIN_POSITION}( ${TRANSFORM_ORIGIN_POSITION})?( 0(px)?)?$`, 'i')

function isSafeUrl(url, protocols) {
    try {
        return protocols.includes(new URL(url, window.location.href).protocol)
    } catch (error) {
        return false
    }
}

function sanitizeStyle(element) {
    Array.from(element.style).forEach((property) => {
        if (!ALLOWED_STYLE_PROPERTIES.has(property)) {
            element.style.removeProperty(property)
        }
    })
    if (element.style.transform && !ALLOWED_TRANSFORM.test(element.style.transform)) {
        element.style.removeProperty('transform')
    }
    // An unbounded origin turns even a shrinking scale into an arbitrary
    // translation, so only keyword and in-box percentage origins are kept.
    if (element.style.transformOrigin
        && !ALLOWED_TRANSFORM_ORIGIN.test(element.style.transformOrigin.trim())) {
        element.style.removeProperty('transform-origin')
        element.style.removeProperty('transform')
    }
    if (element.style.length === 0) {
        element.removeAttribute('style')
    }
}

function sanitizeChildren(element) {
    Array.from(element.children).forEach((child) => {
        const tagName = child.tagName.toLowerCase()
        // `is` cannot be removed once parsed, so the element itself has to go.
        if (!ALLOWED_TAGS.has(tagName) || child.hasAttribute('is')) {
            child.remove()
            return
        }
        const tagAttributes = ALLOWED_TAG_ATTRIBUTES[tagName]
        Array.from(child.attributes).forEach((attribute) => {
            const name = attribute.name.toLowerCase()
            if (name === URL_ATTRIBUTES[tagName]) {
                if (!isSafeUrl(attribute.value, ALLOWED_URL_PROTOCOLS[tagName])) {
                    child.removeAttribute(attribute.name)
                }
            } else if (!ALLOWED_ATTRIBUTES.has(name) && !(tagAttributes && tagAttributes.has(name))) {
                child.removeAttribute(attribute.name)
            }
        })
        if (child.hasAttribute('style')) {
            sanitizeStyle(child)
        }
        sanitizeChildren(child)
    })
}

function sanitizeHtml(html) {
    const doc = new DOMParser().parseFromString(String(html), 'text/html')
    sanitizeChildren(doc.body)
    return doc.body.innerHTML
}

export default {
    name: 'PluginElementHtmlElement',
    props: {
        data: {
            type: Object,
            required: true
        },
        status: {
            required: false
        },
        errors: {
            required: false
        },
    },
    computed: {
        getHtml() {
            return sanitizeHtml(this.data.html ?? 'No HTML returned')
        },
    },
}
</script>

<style scoped>
</style>
