import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import fs from "fs";

const versionData = JSON.parse(fs.readFileSync("./public/version.json", "utf-8"));

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(versionData.version),
    __APP_VERSION_DATA__: JSON.stringify(versionData),
  },
});
