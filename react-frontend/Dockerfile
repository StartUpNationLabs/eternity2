
# Build stage
FROM node:14 as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 80

CMD ["/docker-entrypoint.sh"]
