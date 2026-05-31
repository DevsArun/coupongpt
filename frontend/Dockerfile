# =====================================================================
# CouponGPT frontend — PHP 8.4 + Apache.
# Serves the storefront, user dashboard, and admin mission control.
# =====================================================================
FROM php:8.4-apache

# cURL + JSON are needed by BackendClient.
RUN docker-php-ext-install opcache \
    && a2enmod rewrite headers

# Document root is /public
ENV APACHE_DOCUMENT_ROOT=/var/www/html/public
RUN sed -ri -e 's!/var/www/html!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/sites-available/*.conf \
    && sed -ri -e 's!/var/www/!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

COPY . /var/www/html

# Listen on 8080 to match docker-compose.
RUN sed -ri 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf \
    && sed -ri 's/:80>/:8080>/' /etc/apache2/sites-available/000-default.conf

EXPOSE 8080
CMD ["apache2-foreground"]
