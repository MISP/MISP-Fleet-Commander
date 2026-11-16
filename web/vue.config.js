const { defineConfig } = require('@vue/cli-service');

// In development the UI runs on the vue dev server while the API runs on the backend:
// forward API calls and the socket.io connection so the UI can use same-origin URLs.
const backend = process.env.MFC_BACKEND_URL || 'http://127.0.0.1:5001';
const apiPrefixes = [
  'login', 'instance', 'users', 'fleets', 'servers', 'server-management',
  'plugins', 'pinlists', 'user-settings', 'health', 'jobs', 'baselines', 'static', 'socket.io',
];

module.exports = defineConfig({
  transpileDependencies: true,
  lintOnSave: false,
  devServer: {
    proxy: {
      [`^/(${apiPrefixes.join('|')})(/|$)`]: {
        target: backend,
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
