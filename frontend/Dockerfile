# Dockerfile for Frontend
FROM node:22-slim as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production server
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Copy custom nginx config if needed, or use default
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
