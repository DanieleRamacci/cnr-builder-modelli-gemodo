FROM nginx:1.27-alpine

COPY deploy/coolify-test/index.html /usr/share/nginx/html/index.html
COPY deploy/coolify-test/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
