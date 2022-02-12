# ======
# NGINX
# Configure web server
# ======
FROM nginx:1.21-alpine

# Create certification location and volume
RUN mkdir -p /etc/ssl/certs/ecumene
VOLUME ["/etc/ssl/certs/ecumene"]

# Stage configuration
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d