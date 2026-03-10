FROM node:20-alpine AS builder
WORKDIR /app
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Use a startup script to dynamically set backend host
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
COPY nginx.template.conf /etc/nginx/nginx.template.conf

ENV BACKEND_HOST=backend
ENV BACKEND_PORT=8000

EXPOSE 80
CMD ["/docker-entrypoint.sh"]
