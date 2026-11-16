import { fileURLToPath } from "node:url"
import { defineConfig } from "vitest/config"

// Unit tests of the plain JS modules (helpers, store modules). Components are checked by lint and the build
export default defineConfig({
    resolve: {
        alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    test: {
        include: ["tests/unit/**/*.spec.js"],
        environment: "node",
        setupFiles: ["tests/unit/setup.js"],
    },
})
