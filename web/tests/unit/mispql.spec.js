import { describe, expect, it } from "vitest"
import {
    applyCompletion, capabilityMeta, cellText, completionContext, completionItems, csvCell, errorLine,
    exportFileName, groupErrors, quoteName, resultOutcome, segments, statementKind, statementTable, toCSV, toJSON,
    tokenize, unionFields,
} from "@/helpers/mispql"

const LANGUAGE = {
    keywords: ["AND", "ASC", "BY", "COUNT", "DESC", "DESCRIBE", "FALSE", "FORMAT", "FROM", "IN", "LIKE", "LIMIT",
        "NOT", "OFFSET", "OR", "ORDER", "SELECT", "SHOW", "TABLES", "TRUE", "WHERE"],
    formats: ["table", "flat"],
    tables: [
        { name: "attributes", columns: ["id", "value", "Tag"], aliases: { eventinfo: "Event.info" }, sortable: ["id", "timestamp"] },
        { name: "events", columns: ["id", "info", "Orgc.name"], aliases: { org: "Orgc.name" }, sortable: ["id", "eventinfo"] },
        { name: "objects", columns: ["id", "meta-category"], aliases: {}, sortable: [] },
    ],
    max_limit: 1000,
}

const DESCRIBED = unionFields([
    { server_name: "a", state: "supported", fields: { tags: { type: "string", operators: ["=", "IN", "LIKE"] }, id: { type: "int", operators: ["=", "<"] } } },
    { server_name: "b", state: "supported", fields: { id: { type: "int", operators: ["=", "<"] } } },
    { server_name: "c", state: "not_supported", detail: "404" },
])

// The caret is where `|` is
function at(source) {
    const cursor = source.indexOf("|")
    return { text: source.replace("|", ""), cursor }
}

function offered(source, described = DESCRIBED) {
    const { text, cursor } = at(source)
    const context = completionContext(text, cursor, LANGUAGE.keywords)
    return completionItems(context, { language: LANGUAGE, described }).map(item => item.label)
}

describe("tokens", () => {
    it("reads a statement as mispql's lexer does, without failing", () => {
        const tokens = tokenize("select Id, `meta-category` from Events where v = 'it''s' -- note\nLIMIT 5")
        expect(tokens.map(t => [t.kind, t.value])).toEqual([
            ["keyword", "SELECT"], ["name", "id"], ["symbol", ","], ["name", "meta-category"], ["keyword", "FROM"],
            ["name", "events"], ["keyword", "WHERE"], ["name", "v"], ["symbol", "="], ["string", "it's"],
            ["comment", "-- note"], ["keyword", "LIMIT"], ["number", "5"],
        ])
        const open = tokenize("WHERE a = 'unclosed")
        expect(open[open.length - 1]).toMatchObject({ kind: "string", closed: false, end: 19 })
        expect(tokenize("a ! 12x").map(t => t.kind)).toEqual(["name", "unknown", "unknown"])
        expect(tokenize("a != b <> c")[1].value).toBe("!=")
    })

    it("cuts the text in coloured pieces, marks included", () => {
        const text = "SELECT * FROM events"
        const pieces = segments(text, tokenize(text), [{ start: 14, end: 20 }])
        expect(pieces.map(p => p.text).join("")).toBe(text)
        expect(pieces.find(p => p.text === "events")).toMatchObject({ cls: "q-table", mark: true })
        expect(pieces.find(p => p.text === "SELECT")).toMatchObject({ cls: "q-keyword", mark: false })
        expect(pieces.find(p => p.text === "*").cls).toBe("q-operator")
    })

    it("draws a mistake at the very end as a caret", () => {
        const text = "SELECT * FROM"
        const pieces = segments(text, tokenize(text), [{ start: 13, end: 13 }])
        expect(pieces[pieces.length - 1]).toMatchObject({ caret: true, mark: true })
        expect(pieces.map(p => p.text).join("")).toBe(text)
    })

    it("colours DESCRIBE's table, not DESC's sort direction", () => {
        const describe = segments("DESC events", tokenize("DESC events"))
        expect(describe.find(p => p.text === "events").cls).toBe("q-table")
        const text = "SELECT * FROM events ORDER BY id DESC"
        expect(segments(text, tokenize(text)).find(p => p.text === "id").cls).toBe("q-name")
    })

    it("knows the table of the statement under the caret", () => {
        expect(statementTable("SELECT id FROM Events WHERE id > 1")).toBe("events")
        expect(statementTable("DESCRIBE tags")).toBe("tags")
        expect(statementTable("SELECT id")).toBeNull()
        const two = "SELECT * FROM events; SELECT * FROM tags"
        expect(statementTable(two, two.length)).toBe("tags")
        expect(statementTable(two, 3)).toBe("events")
    })

    it("tells what a statement asks from its first words", () => {
        expect(statementKind("-- note\nselect * from events")).toBe("select")
        expect(statementKind("SELECT COUNT(*) FROM events WHERE id > 1")).toBe("count")
        expect(statementKind("DESC tags")).toBe("describe")
        expect(statementKind("SHOW TABLES")).toBe("show_tables")
        expect(statementKind("SHOW DATABASES")).toBeNull()
        expect(statementKind("")).toBeNull()
    })

    it("quotes names that are not plain words, part by part", () => {
        expect(quoteName("info")).toBe("info")
        expect(quoteName("meta-category")).toBe("`meta-category`")
        expect(quoteName("Event.Orgc.name")).toBe("Event.Orgc.name")
        expect(quoteName("order")).toBe("`order`")
        expect(quoteName("a`b")).toBe("`a``b`")
    })
})

describe("completion", () => {
    it("starts a statement", () => {
        expect(offered("|")).toEqual(["SELECT", "SELECT COUNT(*) FROM", "DESCRIBE", "SHOW TABLES"])
        expect(offered("sh|")).toEqual(["SHOW TABLES"])
        expect(offered("SELECT 1; d|")).toEqual(["DESCRIBE"])
    })

    it("offers the table's columns and aliases in a column list", () => {
        expect(offered("SELECT | FROM events")).toEqual(["*", "COUNT(*)", "id", "info", "Orgc.name", "org", "tags"])
        expect(offered("SELECT id, o| FROM events")).toEqual(["Orgc.name", "org"])
        expect(offered("SELECT Orgc.n| FROM events")).toEqual(["Orgc.name"])
        expect(offered("SELECT * |")).toEqual(["FROM"])
        // No table yet: nothing to say of columns
        expect(offered("SELECT |")).toEqual(["*", "COUNT(*)"])
        expect(offered("SELECT m| FROM objects", { fields: {}, servers: 0 })).toEqual(["meta-category"])
    })

    it("offers tables after FROM and DESCRIBE, then the next clauses", () => {
        expect(offered("SELECT * FROM e|")).toEqual(["events"])
        // From two letters, names that hold them come after those that start with them
        expect(offered("SELECT * FROM ob|")).toEqual(["objects"])
        expect(offered("SELECT * FROM ut|")).toEqual(["attributes"])
        expect(offered("DESCRIBE |")).toEqual(["attributes", "events", "objects"])
        expect(offered("SELECT * FROM events |")).toEqual(["WHERE", "ORDER BY", "LIMIT", "OFFSET", "FORMAT"])
        expect(offered("SHOW |")).toEqual(["TABLES"])
    })

    it("offers the described fields in a WHERE, saying which servers lack one", () => {
        const { text, cursor } = at("SELECT * FROM events WHERE |")
        const items = completionItems(completionContext(text, cursor), { language: LANGUAGE, described: DESCRIBED })
        expect(items.map(item => item.label)).toEqual(["tags", "id", "NOT"])
        expect(items[0].detail).toBe("string · on 1 of 2 servers")
        expect(items[1].detail).toBe("int")
        expect(offered("SELECT * FROM events WHERE id = 1 AND t|")).toEqual(["tags"])
        expect(offered("SELECT * FROM events WHERE NOT (|")).toEqual(["tags", "id", "NOT"])
    })

    it("offers a field's own operators, then what follows a condition", () => {
        expect(offered("SELECT * FROM events WHERE tags |")).toEqual(["=", "IN", "LIKE"])
        expect(offered("SELECT * FROM events WHERE tags L|")).toEqual(["LIKE"])
        expect(offered("SELECT * FROM events WHERE unknown |")).toEqual(["=", "!=", "<", ">", "<=", ">=", "IN", "NOT IN", "LIKE", "NOT LIKE"])
        expect(offered("SELECT * FROM events WHERE tags NOT |")).toEqual(["IN", "LIKE"])
        expect(offered("SELECT * FROM events WHERE tags = 'x' |")).toEqual(["AND", "OR", "ORDER BY", "LIMIT", "OFFSET", "FORMAT"])
        expect(offered("SELECT * FROM events WHERE id IN (1, |")).toEqual([])
        expect(offered("SELECT * FROM events WHERE id IN (1, 2) |")).toContain("AND")
    })

    it("offers sort names, directions, then FORMATs", () => {
        expect(offered("SELECT * FROM events ORDER BY |")).toEqual(["id", "eventinfo"])
        expect(offered("SELECT * FROM events ORDER |")).toEqual(["BY"])
        expect(offered("SELECT * FROM events ORDER BY id |")).toEqual(["ASC", "DESC", "LIMIT", "OFFSET", "FORMAT"])
        expect(offered("SELECT * FROM events LIMIT 5 |")).toEqual(["OFFSET", "FORMAT"])
        expect(offered("SELECT * FROM events FORMAT |")).toEqual(["table", "flat"])
    })

    it("stays quiet in strings, comments and numbers, and once a word is complete", () => {
        expect(completionContext("WHERE a = 'SEL", 14)).toBeNull()
        expect(completionContext("-- SEL", 6)).toBeNull()
        expect(completionContext("LIMIT 10", 8)).toBeNull()
        expect(offered("SELECT * FROM events WHERE|")).toEqual([])
        expect(offered("SELECT * FROM events WHERE tags = |")).toEqual(["TRUE", "FALSE"])
    })

    it("replaces the whole word around the caret, without doubling spaces", () => {
        const { text, cursor } = at("SELECT * FR|OM events")
        const context = completionContext(text, cursor, LANGUAGE.keywords)
        const [from] = completionItems(context, { language: LANGUAGE })
        expect(applyCompletion(text, context, from)).toEqual({ text: "SELECT * FROM events", cursor: 14, insert: "FROM" })
        const end = at("SELECT * FROM ev|")
        const tableContext = completionContext(end.text, end.cursor)
        const [events] = completionItems(tableContext, { language: LANGUAGE })
        expect(applyCompletion(end.text, tableContext, events)).toEqual({ text: "SELECT * FROM events ", cursor: 21, insert: "events " })
    })
})

describe("answers", () => {
    it("unites the fields of the servers that described the table", () => {
        expect(DESCRIBED.servers).toBe(2)
        expect(DESCRIBED.fields.id.servers).toEqual(["a", "b"])
        expect(unionFields(null)).toEqual({ fields: {}, servers: 0 })
    })

    it("groups the same mistake from several servers, in the statement's order", () => {
        const error = (start, message) => ({ start, end: start + 2, line: 1, column: start + 1, message, path: "query" })
        const results = [
            { server_name: "a", response: { outcome: "query_errors", errors: [error(20, "unknown field"), error(5, "bad type")] } },
            { server_name: "b", response: { outcome: "query_errors", errors: [error(20, "unknown field")] } },
            { server_name: "c", response: { outcome: "rows", rows: 3 } },
            { server_name: "d", response: null },
        ]
        const groups = groupErrors(results)
        expect(groups.map(g => [g.start, g.servers])).toEqual([[5, ["a"]], [20, ["a", "b"]]])
    })

    it("places a mistake on its line", () => {
        const text = "SELECT *\nFROM events\nWHERE bogus = 1"
        expect(errorLine(text, text.indexOf("bogus"), text.indexOf("bogus") + 5)).toEqual({ number: 3, text: "WHERE bogus = 1", column: 6, length: 5 })
        expect(errorLine("SELECT * FROM", 13, 13)).toEqual({ number: 1, text: "SELECT * FROM", column: 13, length: 1 })
        expect(errorLine("a\nb", 0, 3).length).toBe(1)
    })

    it("names each server's outcome and capability", () => {
        expect(resultOutcome({ status: "pending" }).label).toBe("Waiting")
        expect(resultOutcome({ status: "skipped", response: { outcome: "not_supported" } })).toMatchObject({ name: "not_supported", tone: "muted" })
        expect(resultOutcome({ status: "cancelled", response: null }).label).toBe("Cancelled")
        expect(resultOutcome({ status: "error", response: { outcome: "weird" } })).toMatchObject({ tone: "critical" })
        expect(capabilityMeta(undefined).label).toBe("Checking…")
        expect(capabilityMeta("no_permission").tone).toBe("warning")
        expect(capabilityMeta("something new").label).toBe("Unclear")
    })
})

describe("export", () => {
    it("writes cells as mispql's table output does", () => {
        expect(cellText(null)).toBe("")
        expect(cellText(false)).toBe("false")
        expect(cellText(["tlp:red", "osint"])).toBe("tlp:red,osint")
        expect(cellText({ a: 1 })).toBe("{\"a\":1}")
        expect(cellText(12)).toBe("12")
    })

    it("keeps spreadsheets from running cells as formulas", () => {
        expect(csvCell("=HYPERLINK(\"x\")")).toBe("\"'=HYPERLINK(\"\"x\"\")\"")
        expect(csvCell("+1")).toBe("'+1")
        expect(csvCell("-5")).toBe("'-5")
        expect(csvCell("@SUM(A1)")).toBe("'@SUM(A1)")
        expect(csvCell("\tx")).toBe("'\tx")
        expect(csvCell("a,b")).toBe("\"a,b\"")
        expect(csvCell("line\nbreak")).toBe("\"line\nbreak\"")
        expect(csvCell("plain")).toBe("plain")
    })

    it("writes CSV and JSON of the shown columns", () => {
        const columns = [{ key: "_server_name", label: "server" }, { key: "id", label: "id" }, { key: "Tag", label: "Tag" }]
        const rows = [{ _server_name: "hub", id: "1", Tag: ["a", "b"], other: "left out" }, { _server_name: "=evil", id: "2" }]
        expect(toCSV(columns, rows)).toBe("server,id,Tag\r\nhub,1,\"a,b\"\r\n'=evil,2,\r\n")
        expect(JSON.parse(toJSON(columns, rows))).toEqual([
            { server: "hub", id: "1", Tag: ["a", "b"] },
            { server: "=evil", id: "2", Tag: null },
        ])
        expect(exportFileName("events", "csv", new Date(2026, 10, 20, 14, 5))).toBe("mispql-events-20261120-1405.csv")
        expect(exportFileName(null, "json", new Date(2026, 0, 2, 3, 4))).toBe("mispql-rows-20260102-0304.json")
    })
})
