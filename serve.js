// Simple static file server for local preview
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const ROOT = path.join(__dirname, 'public');

const MIME = {
  '.html': 'text/html', '.css': 'text/css',
  '.js': 'application/javascript', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon',
  '.json': 'application/json', '.woff2': 'font/woff2',
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg'
};

http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  // Mirror the hosting rewrites for the view URLs (see firebase.json), so /02
  // and /03 are reachable locally too.
  const view = /^\/0[23]\/?$/.test(url);
  const file = path.join(ROOT, (url === '/' || view) ? 'index.html' : url);
  try {
    const data = fs.readFileSync(file);
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'text/plain' });
    res.end(data);
  } catch(e) {
    res.writeHead(404); res.end('not found');
  }
}).listen(PORT, () => console.log('Server ready on port ' + PORT));
