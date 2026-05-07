FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies required by your python packages (like opencv, tesseract, db)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first to cache them
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the whole project (although volume mount will override this locally, it's good practice)
COPY . /app/

# Copy and make entrypoint executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# Production (Railway): set settings module, start with gunicorn
ENV DJANGO_SETTINGS_MODULE=core.settings.production

# Local (docker-compose): entrypoint.sh runs migrations + seeds + devserver
# Production (Railway): CMD below is used directly (entrypoint is bypassed by nixpacks)
ENTRYPOINT ["/entrypoint.sh"]

# Fallback CMD — overridden by entrypoint.sh for local dev.
# Railway uses nixpacks.toml start cmd instead, so this line does not affect prod.
CMD ["echo", "Started via entrypoint.sh"]
