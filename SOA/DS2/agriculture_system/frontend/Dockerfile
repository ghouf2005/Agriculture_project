# ---------- Build stage ----------
FROM node:20-alpine AS build

WORKDIR /app

# Copier package.json + lock
COPY package*.json ./

# Installer dépendances (vite inclus)
RUN npm install

# Copier le reste
COPY . .

# Build Vite
RUN npm run build


# ---------- Production stage ----------
FROM nginx:alpine

# Supprimer config nginx par défaut
RUN rm /etc/nginx/conf.d/default.conf

# Copier build Vite
COPY --from=build /app/dist /usr/share/nginx/html

# Config nginx (optionnel)
COPY nginx.conf /etc/nginx/conf.d

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
