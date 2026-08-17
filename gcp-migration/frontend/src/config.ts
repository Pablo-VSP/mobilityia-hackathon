export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
    chatUrl: import.meta.env.VITE_CHAT_URL || 'http://localhost:8083',
  },
  firebase: {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'ado-mobilityia.firebaseapp.com',
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'ado-mobilityia',
  },
  map: {
    center: [18.5, -99.5] as [number, number],
    zoom: 7,
    tileUrl: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  },
  polling: {
    fleetIntervalMs: 10_000,
    alertsIntervalMs: 30_000,
  },
} as const;
