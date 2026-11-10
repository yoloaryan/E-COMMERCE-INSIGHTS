# Production Container for Nexus Retail AI (HTML5 / CSS3 / Vanilla JS)
FROM nginx:alpine

# Remove default nginx static assets and configuration
RUN rm -rf /usr/share/nginx/html/* && rm -f /etc/nginx/conf.d/default.conf

# Copy reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy web application assets into nginx web root
COPY index.html /usr/share/nginx/html/
COPY style.css /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/
COPY data/nexus_data.json /usr/share/nginx/html/data/nexus_data.json

# Expose HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
