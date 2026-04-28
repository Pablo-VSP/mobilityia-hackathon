export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'https://sutgpijmoh.execute-api.us-east-2.amazonaws.com',
    chatStreamUrl: import.meta.env.VITE_CHAT_STREAM_URL || 'https://ivlaj734gxomoqt57qdsczwkr40gedxy.lambda-url.us-east-2.on.aws/',
  },
  cognito: {
    userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || 'us-east-2_5itNQjtYP',
    clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '7f05s6kerku5ejb58odjj4b1fl',
    region: import.meta.env.VITE_AWS_REGION || 'us-east-2',
  },
  map: {
    center: [18.5, -99.5] as [number, number],
    zoom: 7,
    tileUrl: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  },
  polling: {
    fleetIntervalMs: 10_000,
    alertsIntervalMs: 30_000,
  },
} as const;
