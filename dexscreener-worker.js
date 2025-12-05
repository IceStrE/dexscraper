const { chromium } = require('playwright');
const WebSocket = require('ws');

const DEFAULT_WS_URL =
  process.env.DEX_URL ||
  process.argv[2] ||
  'wss://io.dexscreener.com/dex/screener/v5/pairs/h24/1?rankBy[key]=trendingScoreH6&rankBy[order]=desc&filters[chainIds][0]=solana';

function logTime(message, ...rest) {
  const timestamp = new Date().toISOString().substring(11, 23);
  console.log(`[${timestamp}] ${message}`, ...rest);
}

const wss = new WebSocket.Server({ port: 9999 });

wss.on('listening', () => {
  logTime('Local WS server started on ws://localhost:9999');
});

wss.on('connection', (socket) => {
  logTime('Python client connected');
  socket.on('close', () => logTime('Python client disconnected'));
  socket.on('error', (err) => logTime('Python client error', err));
});

wss.on('error', (err) => {
  logTime('Local WS server error', err);
});

function broadcastToClients(message) {
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  }
}

let browser;

async function shutdown() {
  logTime('Shutting down worker...');
  try {
    if (browser) {
      await browser.close();
    }
  } catch (err) {
    logTime('Error during browser close', err);
  }

  try {
    wss.close();
  } catch (err) {
    logTime('Error during WS server close', err);
  }
}

async function main() {
  logTime('DexScreener worker started');
  logTime(`Using DexScreener WS URL: ${DEFAULT_WS_URL}`);

  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    process.on('SIGINT', async () => {
      logTime('SIGINT received, shutting down...');
      await shutdown();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      logTime('SIGTERM received, shutting down...');
      await shutdown();
      process.exit(0);
    });

    await page.exposeFunction('dexEventFromBrowser', (data) => {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      const preview = payload.length > 200 ? `${payload.slice(0, 200)}...` : payload;
      logTime(`Dex WS message: ${preview}`);
      broadcastToClients(payload);
    });

    await page.goto('https://dexscreener.com', { waitUntil: 'domcontentloaded' });
    logTime('DexScreener page loaded');

    await page.evaluate((wsUrl) => {
      const sock = new WebSocket(wsUrl);

      sock.onopen = () => {
        // eslint-disable-next-line no-console
        console.log('DexScreener WS opened');
      };

      sock.onmessage = (event) => {
        // @ts-ignore
        window.dexEventFromBrowser(event.data);
      };

      sock.onerror = (err) => {
        // eslint-disable-next-line no-console
        console.error('DexScreener WS error', err);
      };

      sock.onclose = () => {
        // eslint-disable-next-line no-console
        console.log('DexScreener WS closed');
      };
    }, DEFAULT_WS_URL);

    logTime('DexScreener WebSocket bridge is running');
  } catch (err) {
    logTime('Fatal error in main', err);
    await shutdown();
    process.exit(1);
  }
}

main();

// Пример Python-клиента:
// pip install websocket-client
//
// import websocket
//
// def on_message(ws, message):
//     print("Got dex event:", message)
//
// ws = websocket.WebSocketApp(
//     "ws://localhost:9999",
//     on_message=on_message
// )
//
// ws.run_forever()
