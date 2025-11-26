FROM ghcr.io/osgeo/gdal:ubuntu-full-3.11.0

WORKDIR /app

# needed for pipx
ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# curl for composer
# PHPUnit requires the "dom", "json", "libxml", "mbstring", "tokenizer", "xml", "xmlwriter" extensions, but the "mbstring" extension is not available.
RUN apt-get update \
    && apt-get install -y \
        curl \
        php \
        php-cli \
        php-dom \
        php-json \
        php-xml \
        php-xmlwriter \
        php-mbstring \
        php-tokenizer \
        php-common \
        php-mysql \
        php-curl \
        python3-pip \
        pipx \
    && pipx install poetry 

COPY --from=composer/composer:latest-bin /composer /usr/bin/composer

COPY . /app

RUN composer install

WORKDIR /app/generate-radaric-mf-values-accumulations

RUN poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi --only main 

WORKDIR /app

CMD ["php", "/app/src/download-and-convert-radar.php"]
