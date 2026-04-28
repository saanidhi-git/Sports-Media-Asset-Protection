FROM python:3.12-slim

# Install system dependencies for OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (Docker cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create weights directory (weights downloaded on startup)
RUN mkdir -p weights

# Render injects PORT env var, default to 8001 for local dev
ENV PORT=8001

EXPOSE 8001

# Start the server
CMD ["python", "main.py"]
