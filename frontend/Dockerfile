FROM node:24-slim AS construccion

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_URL
RUN test -n "$VITE_API_URL" && npm run build

FROM nginx:1.29-alpine

COPY --from=construccion /app/dist /usr/share/nginx/html

EXPOSE 80
