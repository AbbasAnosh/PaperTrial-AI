// vite.config.ts
import { defineConfig } from "file:///F:/project/paper-trail-automator-ai/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///F:/project/paper-trail-automator-ai/frontend/node_modules/@vitejs/plugin-react-swc/index.mjs";
import path from "path";
var __vite_injected_original_dirname = "F:\\project\\paper-trail-automator-ai\\frontend";
var vite_config_default = defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
        rewrite: (path2) => path2.replace(/^\/api/, "")
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        secure: false,
        rewrite: (path2) => path2.replace(/^\/ws/, "")
      }
    }
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "./src")
    },
    extensions: [".js", ".jsx", ".ts", ".tsx", ".json"]
  },
  define: {
    "process.env": process.env,
    process: {
      env: process.env,
      platform: process.platform,
      version: process.version,
      browser: true
    }
  }
}));
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJGOlxcXFxwcm9qZWN0XFxcXHBhcGVyLXRyYWlsLWF1dG9tYXRvci1haVxcXFxmcm9udGVuZFwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiRjpcXFxccHJvamVjdFxcXFxwYXBlci10cmFpbC1hdXRvbWF0b3ItYWlcXFxcZnJvbnRlbmRcXFxcdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Y6L3Byb2plY3QvcGFwZXItdHJhaWwtYXV0b21hdG9yLWFpL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVcIjtcclxuaW1wb3J0IHJlYWN0IGZyb20gXCJAdml0ZWpzL3BsdWdpbi1yZWFjdC1zd2NcIjtcclxuaW1wb3J0IHBhdGggZnJvbSBcInBhdGhcIjtcclxuXHJcbi8vIGh0dHBzOi8vdml0ZWpzLmRldi9jb25maWcvXHJcbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZygoeyBtb2RlIH0pID0+ICh7XHJcbiAgc2VydmVyOiB7XHJcbiAgICBob3N0OiBcIjo6XCIsXHJcbiAgICBwb3J0OiA4MDgwLFxyXG4gICAgcHJveHk6IHtcclxuICAgICAgXCIvYXBpXCI6IHtcclxuICAgICAgICB0YXJnZXQ6IFwiaHR0cDovL2xvY2FsaG9zdDo4MDAwXCIsXHJcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG4gICAgICAgIHNlY3VyZTogZmFsc2UsXHJcbiAgICAgICAgcmV3cml0ZTogKHBhdGgpID0+IHBhdGgucmVwbGFjZSgvXlxcL2FwaS8sIFwiXCIpLFxyXG4gICAgICB9LFxyXG4gICAgICBcIi93c1wiOiB7XHJcbiAgICAgICAgdGFyZ2V0OiBcIndzOi8vbG9jYWxob3N0OjgwMDBcIixcclxuICAgICAgICB3czogdHJ1ZSxcclxuICAgICAgICBzZWN1cmU6IGZhbHNlLFxyXG4gICAgICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC93cy8sIFwiXCIpLFxyXG4gICAgICB9LFxyXG4gICAgfSxcclxuICB9LFxyXG4gIHBsdWdpbnM6IFtyZWFjdCgpXSxcclxuICByZXNvbHZlOiB7XHJcbiAgICBhbGlhczoge1xyXG4gICAgICBcIkBcIjogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgXCIuL3NyY1wiKSxcclxuICAgIH0sXHJcbiAgICBleHRlbnNpb25zOiBbXCIuanNcIiwgXCIuanN4XCIsIFwiLnRzXCIsIFwiLnRzeFwiLCBcIi5qc29uXCJdLFxyXG4gIH0sXHJcbiAgZGVmaW5lOiB7XHJcbiAgICBcInByb2Nlc3MuZW52XCI6IHByb2Nlc3MuZW52LFxyXG4gICAgcHJvY2Vzczoge1xyXG4gICAgICBlbnY6IHByb2Nlc3MuZW52LFxyXG4gICAgICBwbGF0Zm9ybTogcHJvY2Vzcy5wbGF0Zm9ybSxcclxuICAgICAgdmVyc2lvbjogcHJvY2Vzcy52ZXJzaW9uLFxyXG4gICAgICBicm93c2VyOiB0cnVlLFxyXG4gICAgfSxcclxuICB9LFxyXG59KSk7XHJcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBOFQsU0FBUyxvQkFBb0I7QUFDM1YsT0FBTyxXQUFXO0FBQ2xCLE9BQU8sVUFBVTtBQUZqQixJQUFNLG1DQUFtQztBQUt6QyxJQUFPLHNCQUFRLGFBQWEsQ0FBQyxFQUFFLEtBQUssT0FBTztBQUFBLEVBQ3pDLFFBQVE7QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLE9BQU87QUFBQSxNQUNMLFFBQVE7QUFBQSxRQUNOLFFBQVE7QUFBQSxRQUNSLGNBQWM7QUFBQSxRQUNkLFFBQVE7QUFBQSxRQUNSLFNBQVMsQ0FBQ0EsVUFBU0EsTUFBSyxRQUFRLFVBQVUsRUFBRTtBQUFBLE1BQzlDO0FBQUEsTUFDQSxPQUFPO0FBQUEsUUFDTCxRQUFRO0FBQUEsUUFDUixJQUFJO0FBQUEsUUFDSixRQUFRO0FBQUEsUUFDUixTQUFTLENBQUNBLFVBQVNBLE1BQUssUUFBUSxTQUFTLEVBQUU7QUFBQSxNQUM3QztBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQUEsRUFDQSxTQUFTLENBQUMsTUFBTSxDQUFDO0FBQUEsRUFDakIsU0FBUztBQUFBLElBQ1AsT0FBTztBQUFBLE1BQ0wsS0FBSyxLQUFLLFFBQVEsa0NBQVcsT0FBTztBQUFBLElBQ3RDO0FBQUEsSUFDQSxZQUFZLENBQUMsT0FBTyxRQUFRLE9BQU8sUUFBUSxPQUFPO0FBQUEsRUFDcEQ7QUFBQSxFQUNBLFFBQVE7QUFBQSxJQUNOLGVBQWUsUUFBUTtBQUFBLElBQ3ZCLFNBQVM7QUFBQSxNQUNQLEtBQUssUUFBUTtBQUFBLE1BQ2IsVUFBVSxRQUFRO0FBQUEsTUFDbEIsU0FBUyxRQUFRO0FBQUEsTUFDakIsU0FBUztBQUFBLElBQ1g7QUFBQSxFQUNGO0FBQ0YsRUFBRTsiLAogICJuYW1lcyI6IFsicGF0aCJdCn0K
