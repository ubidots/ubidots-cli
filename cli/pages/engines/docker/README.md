# Pages Docker Image

This directory contains the custom Docker image for Ubidots Pages that eliminates the startup delay caused by installing Python dependencies at runtime.

## Overview

**Problem**: When starting a page, the container needs to install Flask, tomli, and flask-cors using pip, which takes several seconds and causes connection errors.

**Solution**: Pre-build a Docker image with all dependencies installed, so pages start instantly.

## Files

- `Dockerfile` - Custom image definition with pre-installed dependencies
- `build_image.py` - Build script for creating the image
- `README.md` - This documentation

## Automatic Building

The custom Docker image is built automatically when you create your first page:

```bash
# First time running this will build the custom image
ubi pages init my-page

# The image is built during page creation, no manual action needed
```

### How It Works

1. **With Custom Image** (fast startup):
   - Image: `ubidots/pages-server:latest`
   - Command: `python /app/server.py`
   - Dependencies: Pre-installed in image
   - Startup time: ~1-2 seconds

2. **Fallback Mode** (slower startup):
   - Image: `python:3.12-slim`
   - Command: `sh -c 'cd /app/page && pip install -q flask tomli flask-cors && python /app/server.py'`
   - Dependencies: Installed at runtime
   - Startup time: ~5-10 seconds

### Automatic Fallback

The system automatically detects if the custom image is available:
- If `ubidots/pages-server:latest` exists → uses custom image
- If not available → falls back to `python:3.12-slim` with runtime pip install

## Dependencies

The custom image includes:
- `flask==3.0.0` - Web framework
- `tomli==2.0.1` - TOML parser
- `flask-cors==4.0.0` - CORS support
- `requests==2.31.0` - HTTP client (for Flask manager)

## Maintenance

### Updating Dependencies

1. Edit `Dockerfile` to update package versions
2. Run `ubi pages build-image` to rebuild
3. Test with `ubi pages start`

### Troubleshooting

**Image build fails during page creation:**
- Check Docker is running
- Verify `page_server.py` exists in templates directory
- Check Docker permissions
- The system will automatically fall back to runtime pip install

**Pages still slow to start:**
- Verify image was built: `docker images | grep ubidots/pages-server`
- Check logs for fallback messages during page creation
- Delete the image and create a new page to rebuild: `docker rmi ubidots/pages-server:latest`

## Development

The build script:
1. Copies `page_server.py` to build context
2. Builds Docker image with dependencies
3. Tags as `ubidots/pages-server:latest`
4. Cleans up temporary files
