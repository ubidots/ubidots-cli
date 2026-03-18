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
    watchdog==3.0.0 \
    docker==7.1.0

# Create a non-root user and group
RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --no-create-home app

# Create app directory
WORKDIR /app

# Copy the page server template
COPY page_server.py /app/server.py

# Create directory for page files (will be mounted at runtime)
RUN mkdir -p /app/page && chown -R app:app /app

# Drop root privileges
USER app

# Set default command
CMD ["python", "/app/server.py"]
