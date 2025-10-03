FROM python:3.12-slim

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies once during image build
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    tomli==2.0.1 \
    flask-cors==4.0.0 \
    requests==2.31.0 \
    watchdog==3.0.0

# Create app directory
WORKDIR /app

# Copy the page server template
COPY page_server.py /app/server.py

# Create directory for page files (will be mounted at runtime)
RUN mkdir -p /app/page

# Set default command
CMD ["python", "/app/server.py"]
