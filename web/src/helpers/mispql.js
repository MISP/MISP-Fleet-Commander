// MispQL as the Query page reads it: tokens to colour a statement, what the caret may be followed by, and the shapes
// results are shown and exported in. Whether a statement is valid is never decided here: mispql decides, through
// the API's check, so the page never disagrees with what runs.

// mispql's keywords (lexer.KEYWORDS). `GET /queries/language` sends the library's own list, which replaces this one
export const KEYWORDS = [
    "AND", "ASC", "BY", "COUNT", "DATABASES", "DESC", "DESCRIBE", "FALSE", "FORMAT", "FROM",
    "IN", "LIKE", "LIMIT", "NOT", "OFFSET", "OR", "ORDER", "SELECT", "SHOW", "TABLES", "TRUE",
    "USE", "WHERE", "WHOAMI",
]

const SYMBOLS = ["!=", "<>", "<=", ">=", "=", "<", ">", "(", ")", ",", ".", "*", ";", "-"]
const COMPARISONS = ["=", "!=", "<>", "<", ">", "<=", ">="]
export const OPERATORS = ["=", "!=", "<", ">", "<=", ">=", "IN", "NOT IN", "LIKE", "NOT LIKE"]
const WORD_CHAR = /[A-Za-z0-9_]/
const PLAIN_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/

function keywordSet(keywords) {
    return keywords instanceof Set ? keywords : new Set(keywords || KEYWORDS)
}

function readQuoted(text, start, quote) {
    let i = start + 1
    let value = ""
    for (;;) {
        const end = text.indexOf(quote, i)
        if (end === -1) {
            return { end: text.length, closed: false, value: value + text.slice(i) }
        }
        value += text.slice(i, end)
        if (text[end + 1] === quote) {
            value += quote
            i = end + 2
        } else {
            return { end: end + 1, closed: true, value }
        }
    }
}

// The statement's tokens, as mispql's lexer reads them, but without ever failing: an unclosed string runs to the end
// (`closed: false`), a character mispql refuses is `unknown`. Kinds: keyword, name, string, number, symbol, comment,
// unknown. Names are lower-cased and keywords upper-cased, as mispql does; backticked names keep their case
export function tokenize(text, keywords) {
    const words = keywordSet(keywords)
    const tokens = []
    const n = text.length
    let i = 0
    while (i < n) {
        const c = text[i]
        if (/\s/.test(c)) {
            i += 1
        } else if (text.startsWith("--", i)) {
            const newline = text.indexOf("\n", i)
            const end = newline === -1 ? n : newline
            tokens.push({ kind: "comment", value: text.slice(i, end), start: i, end })
            i = end
        } else if (c === "'" || c === "\"" || c === "`") {
            const found = readQuoted(text, i, c)
            tokens.push({
                kind: c === "`" ? "name" : "string", value: found.value, start: i, end: found.end,
                closed: found.closed, quoted: c === "`",
            })
            i = found.end
        } else if (WORD_CHAR.test(c)) {
            let end = i
            while (end < n && WORD_CHAR.test(text[end])) {
                end += 1
            }
            const word = text.slice(i, end)
            if (/^[0-9]/.test(word)) {
                tokens.push({ kind: /^[0-9]+$/.test(word) ? "number" : "unknown", value: word, start: i, end })
            } else if (words.has(word.toUpperCase())) {
                tokens.push({ kind: "keyword", value: word.toUpperCase(), start: i, end })
            } else {
                tokens.push({ kind: "name", value: word.toLowerCase(), start: i, end })
            }
            i = end
        } else {
            const symbol = SYMBOLS.find(s => text.startsWith(s, i))
            if (symbol) {
                tokens.push({ kind: "symbol", value: symbol, start: i, end: i + symbol.length })
                i += symbol.length
            } else {
                tokens.push({ kind: "unknown", value: c, start: i, end: i + 1 })
                i += 1
            }
        }
    }
    return tokens
}

function is(token, kind, value) {
    return token !== undefined && token !== null && token.kind === kind && (value === undefined || token.value === value)
}

// The colour class of each token: a name read as a table (after FROM, DESCRIBE) is `table`, comparison and other
// symbols `operator` and `punctuation`
function tokenClass(tokens, index) {
    const token = tokens[index]
    switch (token.kind) {
    case "keyword":
        return ["TRUE", "FALSE"].includes(token.value) ? "q-literal" : "q-keyword"
    case "name": {
        let p = index - 1
        while (p >= 0 && tokens[p].kind === "comment") {
            p -= 1
        }
        const prev = tokens[p]
        const atStatementStart = p < 1 || is(tokens[p - 1], "symbol", ";")
        if (is(prev, "keyword", "FROM") || (atStatementStart && (is(prev, "keyword", "DESCRIBE") || is(prev, "keyword", "DESC")))) {
            return "q-table"
        }
        return "q-name"
    }
    case "string":
        return "q-string"
    case "number":
        return "q-number"
    case "comment":
        return "q-comment"
    case "symbol":
        return COMPARISONS.includes(token.value) || token.value === "*" ? "q-operator" : "q-punctuation"
    default:
        return "q-unknown"
    }
}

// The text cut in pieces to draw it coloured, with the ranges in `marks` ({start, end}) underlined. A mark of no width
// (a mistake at the end of the text: "expected FROM, found end of input") becomes a `caret` piece. Pieces cover the
// whole text, in order
export function segments(text, tokens, marks = []) {
    const n = text.length
    const ranges = (marks || []).map((mark) => {
        const start = Math.max(0, Math.min(mark.start, n))
        return { start, end: Math.max(start, Math.min(mark.end, n)) }
    })
    const cuts = new Set([0, n])
    tokens.forEach((token) => { cuts.add(token.start); cuts.add(Math.min(token.end, n)) })
    ranges.forEach((range) => { cuts.add(range.start); cuts.add(range.end) })
    const points = Array.from(cuts).sort((a, b) => a - b)
    const classes = tokens.map((_, index) => tokenClass(tokens, index))
    const pieces = []
    const carets = new Set(ranges.filter(range => range.start === range.end).map(range => range.start))
    let t = 0
    for (let p = 0; p < points.length; p += 1) {
        const at = points[p]
        if (carets.has(at)) {
            pieces.push({ text: "", cls: null, mark: true, caret: true })
            carets.delete(at)
        }
        const next = points[p + 1]
        if (next === undefined || next === at) {
            continue
        }
        while (t < tokens.length && tokens[t].end <= at) {
            t += 1
        }
        const cls = t < tokens.length && tokens[t].start <= at ? classes[t] : null
        const mark = ranges.some(range => range.start <= at && at < range.end)
        const last = pieces[pieces.length - 1]
        if (last && !last.caret && last.cls === cls && last.mark === mark) {
            last.text += text.slice(at, next)
        } else {
            pieces.push({ text: text.slice(at, next), cls, mark, caret: false })
        }
    }
    return pieces
}

// A name as a statement must write it: in backticks when it is not a plain word or is a keyword, part by part
// (`meta-category`, Event.Orgc.name)
export function quoteName(name, keywords) {
    const words = keywordSet(keywords)
    return String(name).split(".").map((part) => {
        if (PLAIN_NAME.test(part) && !words.has(part.toUpperCase())) {
            return part
        }
        return `\`${part.replace(/`/g, "``")}\``
    }).join(".")
}

// The statement the caret is in: its tokens (comments left out) and where it starts and ends
function statementAround(tokens, offset) {
    let start = 0
    let end = tokens.length
    tokens.forEach((token, index) => {
        if (is(token, "symbol", ";")) {
            if (token.end <= offset) {
                start = index + 1
            } else if (end === tokens.length) {
                end = index
            }
        }
    })
    return tokens.slice(start, end).filter(token => token.kind !== "comment")
}

// The table a statement reads: the name after FROM, or after DESCRIBE. Null when there is none yet
export function statementTable(text, offset = 0, keywords) {
    const statement = statementAround(tokenize(text, keywords), offset)
    for (let i = 0; i < statement.length - 1; i += 1) {
        const token = statement[i]
        const describes = i === 0 && (is(token, "keyword", "DESCRIBE") || is(token, "keyword", "DESC"))
        if ((is(token, "keyword", "FROM") || describes) && statement[i + 1].kind === "name") {
            return statement[i + 1].value
        }
    }
    return null
}

// What a statement asks, from its first words: select, count, describe or show_tables; null otherwise. The run's
// own summaries say it too, but only once a server has answered
export function statementKind(text, keywords) {
    const [first, second] = tokenize(text || "", keywords).filter(token => token.kind !== "comment")
    if (is(first, "keyword", "SELECT")) {
        return is(second, "keyword", "COUNT") ? "count" : "select"
    }
    if (is(first, "keyword", "DESCRIBE") || is(first, "keyword", "DESC")) {
        return "describe"
    }
    return is(first, "keyword", "SHOW") && is(second, "keyword", "TABLES") ? "show_tables" : null
}

// The dotted name that ends at `index` (Event.Orgc.name), as written
function dottedNameBefore(text, tokens, index) {
    let first = index
    while (first >= 2 && is(tokens[first - 1], "symbol", ".") && tokens[first - 2].kind === "name"
           && tokens[first - 2].end === tokens[first - 1].start && tokens[first - 1].end === tokens[first].start) {
        first -= 2
    }
    return text.slice(tokens[first].start, tokens[index].end)
}

const NOTHING = { kinds: [], keywords: [] }
const AFTER_TABLE = ["WHERE", "ORDER BY", "LIMIT", "OFFSET", "FORMAT"]
const AFTER_CONDITION = ["AND", "OR", "ORDER BY", "LIMIT", "OFFSET", "FORMAT"]

// What may come next in a statement whose tokens so far are `statement`: kinds of names (statement, star, column,
// table, field, operator, sort, format) and keywords
function expectations(text, statement) {
    const prev = statement[statement.length - 1]
    const prev2 = statement[statement.length - 2]
    if (!prev) {
        return { kinds: ["statement"], keywords: [] }
    }
    let clause = "start"
    let inList = false
    statement.forEach((token, index) => {
        if (token.kind === "keyword") {
            switch (token.value) {
            case "SELECT": clause = "select"; break
            case "FROM": clause = "from"; break
            case "WHERE": clause = "where"; break
            case "ORDER": clause = "order"; break
            case "BY": if (clause === "order") { clause = "orderby" } break
            case "LIMIT": clause = "limit"; break
            case "OFFSET": clause = "offset"; break
            case "FORMAT": clause = "format"; break
            case "SHOW": clause = "show"; break
            case "DESCRIBE": clause = "describe"; break
            case "DESC": if (index === 0) { clause = "describe" } break
            default: break
            }
        } else if (is(token, "symbol", "(") && is(statement[index - 1], "keyword", "IN")) {
            inList = true
        } else if (is(token, "symbol", ")")) {
            inList = false
        }
    })
    switch (clause) {
    case "select":
        if (is(prev, "keyword", "SELECT")) {
            return { kinds: ["star", "column"], keywords: [] }
        }
        if (is(prev, "symbol", ",")) {
            return { kinds: ["column"], keywords: [] }
        }
        return { kinds: [], keywords: ["FROM"] }
    case "from":
        return is(prev, "keyword", "FROM") ? { kinds: ["table"], keywords: [] } : { kinds: [], keywords: AFTER_TABLE }
    case "where": {
        if (inList) {
            return NOTHING
        }
        const opens = ["WHERE", "AND", "OR"].some(word => is(prev, "keyword", word)) || is(prev, "symbol", "(")
        if (opens) {
            return { kinds: ["field"], keywords: ["NOT"] }
        }
        if (is(prev, "keyword", "NOT")) {
            return prev2 && prev2.kind === "name" ? { kinds: [], keywords: ["IN", "LIKE"] } : { kinds: ["field"], keywords: ["NOT"] }
        }
        if (prev.kind === "name") {
            return { kinds: ["operator"], keywords: [], field: dottedNameBefore(text, statement, statement.length - 1) }
        }
        if (prev.kind === "symbol" && COMPARISONS.includes(prev.value)) {
            return { kinds: [], keywords: ["TRUE", "FALSE"] }
        }
        const ended = ["string", "number"].includes(prev.kind) || is(prev, "keyword", "TRUE")
            || is(prev, "keyword", "FALSE") || is(prev, "symbol", ")")
        return ended ? { kinds: [], keywords: AFTER_CONDITION } : NOTHING
    }
    case "order":
        return { kinds: [], keywords: ["BY"] }
    case "orderby":
        if (is(prev, "keyword", "BY") || is(prev, "symbol", ",")) {
            return { kinds: ["sort"], keywords: [] }
        }
        if (prev.kind === "name") {
            return { kinds: [], keywords: ["ASC", "DESC", "LIMIT", "OFFSET", "FORMAT"] }
        }
        return is(prev, "keyword", "ASC") || is(prev, "keyword", "DESC") ? { kinds: [], keywords: ["LIMIT", "OFFSET", "FORMAT"] } : NOTHING
    case "limit":
        return prev.kind === "number" ? { kinds: [], keywords: ["OFFSET", "FORMAT"] } : NOTHING
    case "offset":
        return prev.kind === "number" ? { kinds: [], keywords: ["FORMAT"] } : NOTHING
    case "format":
        return is(prev, "keyword", "FORMAT") ? { kinds: ["format"], keywords: [] } : NOTHING
    case "describe":
        return is(prev, "keyword", "DESCRIBE") || is(prev, "keyword", "DESC") ? { kinds: ["table"], keywords: [] } : NOTHING
    case "show":
        return is(prev, "keyword", "SHOW") ? { kinds: [], keywords: ["TABLES"] } : NOTHING
    default:
        return NOTHING
    }
}

// Where the caret is, for completion: the word being typed (`from`..`to`, `prefix`), what may be written there, and
// the statement's table. Null inside a string or a comment, or while typing a number
export function completionContext(text, cursor, keywords) {
    const words = keywordSet(keywords)
    const before = tokenize(text.slice(0, cursor), words)
    const last = before[before.length - 1]
    if (last && last.end === cursor) {
        if (last.kind === "comment" || (last.kind === "string" && !last.closed)
            || (last.kind === "name" && last.quoted && !last.closed) || last.kind === "number") {
            return null
        }
    }
    let k = before.length
    let from = cursor
    const typing = last && last.end === cursor && ((last.kind === "name" && !last.quoted) || last.kind === "keyword")
    if (typing) {
        k -= 1
        from = last.start
    }
    // A dotted name being written (Orgc.na, Event.): complete it whole
    if (k > 0 && is(before[k - 1], "symbol", ".") && before[k - 1].end === from) {
        let first = k - 1
        while (first >= 1 && before[first - 1].kind === "name" && before[first - 1].end === before[first].start) {
            first -= 1
            if (first >= 1 && is(before[first - 1], "symbol", ".") && before[first - 1].end === before[first].start) {
                first -= 1
            } else {
                break
            }
        }
        if (first < k - 1) {
            k = first
            from = before[first].start
        }
    }
    let to = cursor
    while (to < text.length && WORD_CHAR.test(text[to])) {
        to += 1
    }
    const statement = statementAround(before.slice(0, k), from)
    const expected = expectations(text.slice(0, cursor), statement)
    return {
        from,
        to,
        prefix: text.slice(from, cursor),
        kinds: expected.kinds,
        keywords: expected.keywords,
        field: expected.field || null,
        table: statementTable(text, from, words),
    }
}

// The fields of a table as the chosen servers describe it: each field once, with the servers that have it.
// `answers` are `GET /queries/describe` entries ({server_id, server_name, state, fields})
export function unionFields(answers) {
    const described = (answers || []).filter(answer => answer && answer.state === "supported" && answer.fields)
    const fields = {}
    described.forEach((answer) => {
        Object.entries(answer.fields).forEach(([name, info]) => {
            if (!fields[name]) {
                fields[name] = { name, type: info.type, operators: info.operators || [], level: info.level, servers: [] }
            }
            fields[name].servers.push(answer.server_name)
        })
    })
    return { fields, servers: described.length }
}

function lookup(map, name) {
    if (!map || !name) {
        return null
    }
    if (map[name]) {
        return map[name]
    }
    const lower = name.toLowerCase()
    const key = Object.keys(map).find(candidate => candidate.toLowerCase() === lower)
    return key ? map[key] : null
}

function servedBy(field, total) {
    return total > 1 && field.servers.length < total ? `on ${field.servers.length} of ${total} servers` : ""
}

// What the completion list offers in `context`. `catalog`: `language` (GET /queries/language) and `described` (the
// result of unionFields for the statement's table, when known). Items: {label, insert, detail, kind}
export function completionItems(context, catalog = {}) {
    if (!context) {
        return []
    }
    const language = catalog.language || {}
    const words = keywordSet(language.keywords)
    const table = (language.tables || []).find(entry => entry.name === context.table) || null
    const described = catalog.described || { fields: {}, servers: 0 }
    const items = []
    const seen = new Set()
    const add = (label, insert, detail, kind) => {
        const key = `${kind === "keyword" ? "k" : "n"}:${label.toLowerCase()}`
        if (!seen.has(key)) {
            seen.add(key)
            items.push({ label, insert, detail: detail || "", kind })
        }
    }
    const kinds = new Set(context.kinds)
    if (kinds.has("statement")) {
        add("SELECT", "SELECT ", "rows", "keyword")
        add("SELECT COUNT(*) FROM", "SELECT COUNT(*) FROM ", "a count", "keyword")
        add("DESCRIBE", "DESCRIBE ", "a table's fields", "keyword")
        add("SHOW TABLES", "SHOW TABLES", "the tables each server answers", "keyword")
    }
    if (kinds.has("star")) {
        add("*", "* ", "the table's columns", "operator")
        add("COUNT(*)", "COUNT(*) ", "how many rows match", "keyword")
    }
    if (kinds.has("column") && table) {
        table.columns.forEach(column => add(column, quoteName(column, words), "default column", "column"))
        Object.entries(table.aliases || {}).forEach(([alias, target]) => add(alias, quoteName(alias, words), target, "column"))
        Object.values(described.fields).forEach(field => add(field.name, quoteName(field.name, words), field.type, "column"))
    }
    if (kinds.has("table")) {
        (language.tables || []).forEach(entry => add(entry.name, `${quoteName(entry.name, words)} `, "", "table"))
    }
    if (kinds.has("field")) {
        const fields = Object.values(described.fields)
        fields.forEach((field) => {
            const note = servedBy(field, described.servers)
            add(field.name, `${quoteName(field.name, words)} `, [field.type, note].filter(Boolean).join(" · "), "field")
        })
        if (fields.length === 0 && table) {
            Object.keys(table.aliases || {}).forEach(alias => add(alias, `${quoteName(alias, words)} `, "", "field"))
        }
    }
    if (kinds.has("operator")) {
        const field = lookup(described.fields, context.field)
        const operators = field && field.operators.length ? field.operators : OPERATORS
        operators.forEach(operator => add(operator, `${operator} `, field ? field.type : "", "operator"))
    }
    if (kinds.has("sort") && table) {
        table.sortable.forEach(name => add(name, quoteName(name, words), "", "sort"))
    }
    if (kinds.has("format")) {
        (language.formats || ["table", "flat"]).forEach(format => add(format, format, "", "format"))
    }
    context.keywords.forEach(phrase => add(phrase, `${phrase} `, "", "keyword"))

    const prefix = context.prefix.toLowerCase()
    if (prefix === "") {
        return items
    }
    const starts = items.filter(item => item.label.toLowerCase().startsWith(prefix))
    const inside = prefix.length >= 2
        ? items.filter(item => !item.label.toLowerCase().startsWith(prefix) && item.label.toLowerCase().includes(prefix))
        : []
    const found = starts.concat(inside)
    // Nothing to offer once the word is written in full
    if (found.length === 1 && found[0].label.toLowerCase() === prefix) {
        return []
    }
    return found
}

// The text once `item` replaces the word around the caret, and where the caret goes. No doubled space
export function applyCompletion(text, context, item) {
    let insert = item.insert
    let skip = 0
    if (insert.endsWith(" ") && text.charAt(context.to) === " ") {
        insert = insert.slice(0, -1)
        skip = 1
    }
    return {
        text: text.slice(0, context.from) + insert + text.slice(context.to),
        cursor: context.from + insert.length + skip,
        insert,
    }
}

// Where a mistake is, to draw it under its line: the line's number and text, the column of the mistake in it and how
// many characters to underline (at least one, not past the line's end)
export function errorLine(text, start, end) {
    const offset = Math.max(0, Math.min(start, text.length))
    const lineStart = text.lastIndexOf("\n", offset - 1) + 1
    const newline = text.indexOf("\n", offset)
    const lineEnd = newline === -1 ? text.length : newline
    const number = text.slice(0, lineStart).split("\n").length
    const column = offset - lineStart
    const length = Math.max(1, Math.min(Math.max(end, offset), lineEnd) - offset)
    return { number, text: text.slice(lineStart, lineEnd), column, length }
}

// MISP's mistakes from every server, each place and message once, with the servers that reported it, in the order
// they appear in the statement
export function groupErrors(results) {
    const groups = {}
    ;(results || []).forEach((result) => {
        const response = result && result.response
        if (!response || !Array.isArray(response.errors) || !["query_errors", "invalid"].includes(response.outcome)) {
            return
        }
        response.errors.forEach((error) => {
            const key = `${error.start}:${error.end}:${error.message}`
            if (!groups[key]) {
                groups[key] = Object.assign({}, error, { servers: [] })
            }
            if (!groups[key].servers.includes(result.server_name)) {
                groups[key].servers.push(result.server_name)
            }
        })
    })
    return Object.values(groups).sort((a, b) => (a.start - b.start) || (a.end - b.end))
}

// What each outcome of a server's run is called, and its tone (global.css job tones)
export const OUTCOME_META = {
    rows: { label: "Rows", tone: "ok", icon: "fa-table" },
    count: { label: "Counted", tone: "ok", icon: "fa-hashtag" },
    describe: { label: "Described", tone: "ok", icon: "fa-list" },
    tables: { label: "Answered", tone: "ok", icon: "fa-table-list" },
    not_supported: { label: "Not supported", tone: "muted", icon: "fa-ban", help: "This MISP has no complex queries: it would ignore the WHERE, so nothing was searched" },
    no_permission: { label: "No permission", tone: "warning", icon: "fa-lock", help: "The key's role may not use complex queries" },
    unavailable: { label: "Refused", tone: "warning", icon: "fa-lock", help: "The server answered 403: the key may not use complex queries, or this MISP has none" },
    unknown: { label: "Unclear answer", tone: "warning", icon: "fa-circle-question", help: "The server's answer did not say whether it runs complex queries" },
    query_errors: { label: "Query errors", tone: "critical", icon: "fa-triangle-exclamation", help: "MISP refused the query: see the mistakes on the statement" },
    invalid: { label: "Invalid", tone: "critical", icon: "fa-triangle-exclamation", help: "The statement no longer passes the checks" },
    unreachable: { label: "Unreachable", tone: "critical", icon: "fa-plug-circle-xmark" },
    timeout: { label: "Timed out", tone: "critical", icon: "fa-hourglass-end" },
    too_large: { label: "Too large", tone: "critical", icon: "fa-weight-hanging", help: "The answer is larger than the Queries setting allows" },
    refused: { label: "HTTP error", tone: "critical", icon: "fa-circle-xmark" },
    bad_answer: { label: "Unexpected answer", tone: "critical", icon: "fa-circle-xmark" },
}

const PENDING_META = { label: "Waiting", tone: "muted", icon: "fa-clock" }
const CANCELLED_META = { label: "Cancelled", tone: "muted", icon: "fa-ban" }

// The outcome of one server's part in a run, from its job result
export function resultOutcome(result) {
    if (!result || result.status === "pending") {
        return Object.assign({ name: "pending" }, PENDING_META)
    }
    const name = result.response && result.response.outcome
    if (name && OUTCOME_META[name]) {
        return Object.assign({ name }, OUTCOME_META[name])
    }
    if (result.status === "cancelled") {
        return Object.assign({ name: "cancelled" }, CANCELLED_META)
    }
    return { name: name || result.status, label: result.status === "ok" ? "Done" : "Failed", tone: result.status === "ok" ? "ok" : "critical", icon: "fa-circle-xmark" }
}

// Whether a server may be asked a query, as its capability says (`GET /queries/capabilities`)
export const CAPABILITY_META = {
    supported: { label: "Supported", tone: "ok", icon: "fa-circle-check", short: "can run queries" },
    not_supported: { label: "Not supported", tone: "muted", icon: "fa-ban", short: "no complex queries" },
    no_permission: { label: "No permission", tone: "warning", icon: "fa-lock", short: "key lacks the permission" },
    unavailable: { label: "Refused", tone: "warning", icon: "fa-lock", short: "answered 403" },
    unreachable: { label: "Unreachable", tone: "critical", icon: "fa-plug-circle-xmark", short: "no answer" },
    unknown: { label: "Unclear", tone: "warning", icon: "fa-circle-question", short: "unclear answer" },
}

export function capabilityMeta(state) {
    if (!state) {
        return { label: "Checking…", tone: "muted", icon: "fa-spinner fa-spin", short: "being checked" }
    }
    return CAPABILITY_META[state] || CAPABILITY_META.unknown
}

// A cell as text: lists joined with commas, as mispql's table output does
export function cellText(value) {
    if (value === null || value === undefined) {
        return ""
    }
    if (typeof value === "boolean") {
        return value ? "true" : "false"
    }
    if (Array.isArray(value)) {
        return value.map(cellText).join(",")
    }
    if (typeof value === "object") {
        return JSON.stringify(value)
    }
    return String(value)
}

// A CSV cell: a spreadsheet would run text starting with = + - @ tab or CR as a formula, so such text gets a
// leading quote; then RFC 4180 quoting
export function csvCell(value) {
    let text = cellText(value)
    if (/^[=+\-@\t\r]/.test(text)) {
        text = `'${text}`
    }
    if (/[",\r\n]/.test(text)) {
        text = `"${text.replace(/"/g, "\"\"")}"`
    }
    return text
}

// Rows as CSV: `columns` are [{key, label}], each row an object
export function toCSV(columns, rows) {
    const lines = [columns.map(column => csvCell(column.label)).join(",")]
    rows.forEach((row) => {
        lines.push(columns.map(column => csvCell(row[column.key])).join(","))
    })
    return `${lines.join("\r\n")}\r\n`
}

// Rows as JSON: each row an object of the shown columns, values as the server sent them
export function toJSON(columns, rows) {
    return JSON.stringify(rows.map((row) => {
        const entry = {}
        columns.forEach((column) => {
            entry[column.label] = row[column.key] === undefined ? null : row[column.key]
        })
        return entry
    }), null, 2)
}

// A file name for an export: mispql-events-20261120-1405.csv
export function exportFileName(table, extension, date = new Date()) {
    const pad = value => String(value).padStart(2, "0")
    const stamp = `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}`
    const name = String(table || "rows").replace(/[^A-Za-z0-9_-]/g, "_")
    return `mispql-${name}-${stamp}.${extension}`
}

// Statements to start from: valid on any server with complex queries
export const EXAMPLES = [
    { title: "How many tlp:red events each server holds", statement: "SELECT COUNT(*) FROM events WHERE tags = 'tlp:red'" },
    { title: "Where an indicator is", statement: "SELECT * FROM attributes\nWHERE value = '198.51.100.23'\nLIMIT 100" },
    { title: "Latest published events", statement: "SELECT id, date, eventinfo, org, tags FROM events\nWHERE published = TRUE\nORDER BY publish_timestamp DESC\nLIMIT 20" },
    { title: "The fields of a table", statement: "DESCRIBE events" },
    { title: "The tables each server answers", statement: "SHOW TABLES" },
]
