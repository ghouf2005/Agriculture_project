# Setup Instructions

## Backend (Django + DRF + SimpleJWT)
1) From `SOA/DS2/agriculture_system/agriculture_sys_project`, create/activate a Python env (Pipenv or venv) and install deps: `pipenv install`.
2) Env vars (shell or `.env`): `SECRET_KEY` (prod), `JWT_SECRET` (optional, defaults to `SECRET_KEY`), `JWT_ACCESS_LIFETIME_MINUTES` (default 60), `JWT_REFRESH_LIFETIME_DAYS` (default 30).
3) Migrate DB: `python manage.py migrate`.
4) Create admin: `python manage.py createsuperuser`.
5) Run API: `python manage.py runserver` (http://localhost:8000/).
6) Docs live: Swagger at http://localhost:8000/api/docs, Redoc at http://localhost:8000/api/redoc.

## Frontend (Vue 3 + Vite)
1) From `SOA/DS2/agriculture_system/frontend`, install deps: `npm install`.
2) Add `.env` or `.env.local` with `VITE_API_BASE_URL=http://localhost:8000/api`.
3) Dev server: `npm run dev` (http://localhost:5173). Build: `npm run build`. Type-check: `npm run type-check`.

## Simulator 
1) From `SOA/DS2/simulator`, set API URL/auth in `config.py`.
2) Run stream: `python simulator.py` (posts sensor readings to backend).
