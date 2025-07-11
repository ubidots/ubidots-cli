# Ubidots Pages Development Guide

## Overview

The Ubidots CLI now includes a powerful local development environment for creating and testing Custom Application Pages. This feature provides a CLASP-like development experience with live preview, hot reload, and a simulated Ubidots dashboard context.

## Quick Start

### 1. Start Development Server

```bash
ubidots pages dev
```

This command will:
- Start a development server on `http://localhost:3000` with mocked Ubidots context
- Set up an iframe that watches for content on `http://localhost:3001`
- Automatically open your browser to the development preview
- Display a beautiful mocked Ubidots dashboard with navigation bar

### 2. Serve Your Custom Page

In a separate terminal, serve your custom page content on port 3001:

```bash
# Using Python's built-in server
cd your-page-directory
python3 -m http.server 3001

# Or using Node.js
npx http-server -p 3001

# Or any other local server
```

### 3. Start Developing

Your custom page will automatically appear in the iframe within the Ubidots context. Changes to your HTML, CSS, and JavaScript files will be reflected immediately.

## Development Environment Features

### Mocked Ubidots Context Bar
- **Authentic UI**: Pixel-perfect recreation of the Ubidots dashboard interface
- **Navigation**: Realistic navigation menu (Dashboard, Devices, Variables, Functions, Custom Pages, Analytics)
- **User Context**: Simulated user avatar and developer mode indicator
- **Status Indicators**: Real-time connection status with your development content

### Real-time Preview
- **Iframe Integration**: Your custom page loads seamlessly within the Ubidots context
- **Auto-refresh**: Automatic detection and loading of content changes
- **Error Handling**: Graceful fallback when content isn't available
- **Connection Status**: Visual indicators for development server connectivity

### Developer Experience
- **One Command Setup**: No complex configuration needed
- **Automatic Browser Opening**: Instantly see your development environment
- **Hot Reload Support**: Changes reflect immediately (when using compatible dev servers)
- **Mobile Responsive**: Test your pages across different viewport sizes

## Command Reference

### `ubidots pages dev`

Start the local development server with Ubidots context preview.

**Options:**
- `--port` (default: 3000): Port for the main development server
- `--iframe-port` (default: 3001): Port where your custom page should be served
- `--auto-open` / `--no-auto-open` (default: true): Automatically open browser
- `--verbose`: Enable detailed logging

**Examples:**

```bash
# Basic usage
ubidots pages dev

# Custom ports
ubidots pages dev --port 8000 --iframe-port 8001

# Don't open browser automatically
ubidots pages dev --no-auto-open

# Verbose logging
ubidots pages dev --verbose
```

## Page Development Best Practices

### 1. Project Structure

Organize your custom page project following Ubidots conventions:

```
my-custom-page/
├── manifest.toml           # Ubidots page manifest
├── src/
│   ├── index.html         # Main HTML file
│   ├── styles.css         # Custom styles
│   ├── script.js          # JavaScript functionality
│   └── assets/            # Images, icons, etc.
├── public/
│   └── static/            # Static files
└── README.md              # Project documentation
```

### 2. Ubidots Integration Patterns

#### Authentication Context
```javascript
// Access user context (simulated in development)
window.addEventListener('message', (event) => {
  if (event.data.type === 'USER_CONTEXT') {
    const { userId, orgId, permissions } = event.data.payload;
    // Use context in your application
  }
});
```

#### API Integration
```javascript
// Make API calls to Ubidots (use development proxies)
async function fetchDeviceData() {
  try {
    const response = await fetch('/api/v1.6/devices/', {
      headers: {
        'X-Auth-Token': 'your-dev-token',
        'Content-Type': 'application/json'
      }
    });
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
  }
}
```

### 3. Responsive Design

Ensure your pages work well within the Ubidots dashboard context:

```css
/* Responsive design for Ubidots context */
.page-container {
  max-width: 100%;
  padding: 20px;
  box-sizing: border-box;
}

/* Mobile optimization */
@media (max-width: 768px) {
  .page-container {
    padding: 10px;
  }
}

/* Adapt to iframe constraints */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
```

## Development Workflow

### 1. Page Creation
1. Create a new directory for your custom page
2. Initialize with basic HTML structure
3. Start the Ubidots development server: `ubidots pages dev`
4. Serve your content on the specified iframe port

### 2. Iterative Development
1. Make changes to your HTML, CSS, or JavaScript
2. Refresh your local server or use hot reload tools
3. See changes instantly in the Ubidots context
4. Test responsive behavior and user interactions

### 3. Integration Testing
1. Test API integrations with mock data
2. Verify responsive design across devices
3. Ensure proper error handling
4. Validate user experience within Ubidots context

### 4. Deployment Preparation
1. Build optimized assets for production
2. Update manifest.toml with page metadata
3. Test final build in development environment
4. Deploy to Ubidots platform

## Troubleshooting

### Common Issues

#### "Waiting for content..." Message
- **Cause**: No content being served on the iframe port
- **Solution**: Ensure you have a local server running on the specified iframe port (default: 3001)

#### Content Not Loading
- **Cause**: CORS issues or server not responding
- **Solution**: Check that your local server allows cross-origin requests

#### Page Not Refreshing
- **Cause**: Browser caching or server not restarting
- **Solution**: Hard refresh browser (Ctrl+F5) or restart your local server

### Debug Mode

Enable verbose logging to see detailed information:

```bash
ubidots pages dev --verbose
```

This will show:
- Server startup details
- Request logging
- Error messages
- Connection status updates

## Advanced Features

### PostMessage Communication

The development environment supports PostMessage API for advanced iframe communication:

```javascript
// Send message to parent (Ubidots context)
window.parent.postMessage({
  type: 'CUSTOM_EVENT',
  payload: { action: 'navigate', url: '/devices' }
}, '*');

// Listen for messages from parent
window.addEventListener('message', (event) => {
  if (event.origin !== window.location.origin) return;
  
  switch (event.data.type) {
    case 'USER_CONTEXT':
      handleUserContext(event.data.payload);
      break;
    case 'DEVICE_DATA':
      updateDeviceDisplay(event.data.payload);
      break;
  }
});
```

### Hot Reload Integration

For frameworks with hot reload support (React, Vue, etc.):

```javascript
// React example with hot reload
if (module.hot) {
  module.hot.accept('./App', () => {
    // Component will hot reload automatically
  });
}
```

## Migration from Dev Center

Moving from the web-based Dev Center to local development:

1. **Export Existing Code**: Copy your existing manifest.toml, HTML, CSS, and JS
2. **Setup Local Environment**: Create project structure and start development server
3. **Test Functionality**: Ensure all features work in the local environment
4. **Enhance with Hot Reload**: Add build tools for better development experience

## Examples

### Basic Dashboard Page
```html
<!DOCTYPE html>
<html>
<head>
    <title>My Dashboard</title>
    <style>
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
        .widget { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="widget">
            <h3>Device Status</h3>
            <p>All systems operational</p>
        </div>
        <div class="widget">
            <h3>Latest Data</h3>
            <p>Updated 2 minutes ago</p>
        </div>
    </div>
</body>
</html>
```

### Interactive Control Panel
```html
<!DOCTYPE html>
<html>
<head>
    <title>Control Panel</title>
    <script>
        function sendCommand(device, action) {
            console.log(`Sending ${action} to ${device}`);
            // Implement API call here
        }
    </script>
</head>
<body>
    <h2>Device Control Panel</h2>
    <button onclick="sendCommand('device_001', 'start')">Start Device</button>
    <button onclick="sendCommand('device_001', 'stop')">Stop Device</button>
</body>
</html>
```

## Support

For issues or questions about custom page development:

1. Check this documentation
2. Review the troubleshooting section
3. Test with the provided examples
4. Contact the development team with specific error messages

---

*This feature enhances the Ubidots development experience by providing modern, local development tools similar to industry-standard frameworks like CLASP.*