FROM nginx:1.27-alpine

COPY deploy/coolify-test/ /usr/share/nginx/html/

EXPOSE 80
