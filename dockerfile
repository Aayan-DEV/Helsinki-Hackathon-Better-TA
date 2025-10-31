FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install dependencies first (better build cache)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app

# Expose the app port
EXPOSE 8000

# Start Gunicorn; uses $PORT if provided (e.g., from hosting)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} hackathon.wsgi:application"]