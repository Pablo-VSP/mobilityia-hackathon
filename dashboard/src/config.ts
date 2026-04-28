export const config = {
  api: {
    baseUrl: 'https://sutgpijmoh.execute-api.us-east-2.amazonaws.com',
    chatStreamUrl: 'https://ivlaj734gxomoqt57qdsczwkr40gedxy.lambda-url.us-east-2.on.aws/',
  },
  cognito: {
    userPoolId: 'us-east-2_5itNQjtYP',
    clientId: '7f05s6kerku5ejb58odjj4b1fl',
    region: 'us-east-2',
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
