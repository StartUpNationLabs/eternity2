FROM node:lts AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN ls -la
RUN npm run build
RUN ls -la

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 80

CMD ["/docker-entrypoint.sh"]
