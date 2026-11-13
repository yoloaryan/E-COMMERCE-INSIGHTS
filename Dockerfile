# Production Container for Prism Retail (HTML5 / CSS3 / Vanilla JS)
FROM nginx:alpine

# Remove default nginx static assets and configuration
RUN rm -rf /usr/share/nginx/html/* && rm -f /etc/nginx/conf.d/default.conf

# Copy reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy web application assets into nginx web root
COPY index.html /usr/share/nginx/html/
COPY style.css /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/
COPY js/ /usr/share/nginx/html/js/
COPY data/nexus_data.json /usr/share/nginx/html/data/nexus_data.json

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
