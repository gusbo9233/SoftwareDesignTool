import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, "../app/static/js"),
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, "src/main.tsx"),
      output: {
        entryFileNames: "diagram-editor.js",
        chunkFileNames: "diagram-editor-[name].js",
        assetFileNames: "diagram-editor[extname]",
      },
    },
  },
});
