# AI-Enhanced Crop Monitoring Frontend

Vue 3 + Vite dashboard for the AI-Enhanced Crop Monitoring and Sensor-Based Anomaly Detection Platform. It consumes the Django REST API to show plots, sensor trends, anomalies, and agent recommendations.

## Stack
- Vue 3 + Vite (TypeScript)
- Vue Router 4
- Pinia for auth state (JWT)
- Axios for API calls
- Chart.js + vue-chartjs for time-series charts
- Bootstrap 5 for layout and styling

## Quick start
1. Install Node.js 18+.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Create a `.env` (or `.env.local`) at the project root to point to the Django API:
   ```bash
   VITE_API_BASE_URL=http://localhost:8000/api
   ```
4. Run the dev server:
   ```bash
   npm run dev
   ```
   The app serves at http://localhost:5173/ by default.
5. Build for production:
   ```bash
   npm run build
   ```
6. (Optional) Type-check:
   ```bash
   npm run type-check
   ```

## Pages
- **Login**: POSTs to `/api/auth/token/`, stores JWT in `localStorage`, and redirects to the dashboard.
- **Dashboard**: Lists plots from `/api/plots/`, highlighting plots with recent anomalies from `/api/anomalies/`.
- **Plot Detail**: Shows time-series charts of `/api/sensor-readings/?plot=<id>` and anomalies from `/api/anomalies/?plot=<id>`. Anomalous timestamps are highlighted on the chart.
- **Alerts**: Displays recommendations from `/api/recommendations/` with related anomalies.

## Assumed API shapes
- `/plots/` → `{ id, name?, location?, description?, farm }[]`
- `/sensor-readings/` → `{ timestamp, moisture, temperature, humidity, plot }[]`
- `/anomalies/` → `{ id, plot, timestamp, description?, type?, severity? }[]`
- `/recommendations/` → `{ id, anomaly_id?, anomaly?, plot?, action, explanation?, created_at?, timestamp? }[]`

If your API differs, adjust the field names in the view files under `src/views`.

## Notes
- Auth headers are added via an Axios interceptor that reads `agri_token` from `localStorage`.
- Basic polling (30s) is enabled on Dashboard, Plot Detail, and Alerts for a near-real-time feel.
- Styling uses Bootstrap (via CDN and import). Adjust as needed in `App.vue` or per-view styles.
