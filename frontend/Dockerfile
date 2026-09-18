# Two targets: `dev` (infra/local/compose.yaml, ng serve with hot reload) and
# `production` (docker-compose.coolify.yml, static build behind nginx). Neither
# is the default - callers must pass --target explicitly (both compose files do).

FROM node:24-slim AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

FROM base AS dev
EXPOSE 4200
CMD ["sh", "-c", "./scripts/genera-runtime-config.sh && npx ng serve --host 0.0.0.0 --port 4200"]

FROM base AS build
RUN npx ng build --configuration production

FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist/gemodo-frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY scripts/docker-entrypoint-nginx.sh /docker-entrypoint-nginx.sh
RUN chmod +x /docker-entrypoint-nginx.sh
EXPOSE 80
CMD ["/docker-entrypoint-nginx.sh"]
