FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data files
COPY . .

# Expose port (for local testing, railway handles ports dynamically)
EXPOSE 8000

# Start server using uvicorn, bind to the $PORT env variable which is set by Railway
CMD uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}
