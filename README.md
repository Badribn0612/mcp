# img-gen

An MCP (Model Context Protocol) server that provides image generation and weather services for Claude Desktop and other MCP-compatible clients.

## Features

### 🎨 Image Generation
- Generate images using Google's Gemini 2.5 Flash Image model
- Automatic image compression and resizing to optimize token usage
- Base64 encoding for seamless integration with MCP clients
- Comprehensive logging and error handling

### 🌤️ Weather Services
- Get weather alerts for US states
- Fetch detailed weather forecasts by latitude/longitude
- Uses the National Weather Service (NWS) API

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Google Gemini API key (for image generation)
- Claude Desktop (optional, for MCP integration)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd img_gen
```

2. Install dependencies using `uv`:
```bash
uv sync
```

## Configuration

### Google Gemini API Key

For image generation, you need to set up your Google Gemini API key. Update the `API_KEY` variable in `image_generation.py`:

```python
API_KEY = "your-api-key-here"
```

Alternatively, you can modify the code to read from an environment variable for better security.

### Claude Desktop Integration

To use this MCP server with Claude Desktop, add the following configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Linux**: `~/.config/Claude/claude_desktop_config.json`

#### Image Generation Server Configuration:
```json
{
  "mcpServers": {
    "image_generation": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/img_gen",
        "run",
        "image_generation.py"
      ]
    }
  }
}
```

#### Weather Server Configuration:
```json
{
  "mcpServers": {
    "weather": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/img_gen",
        "run",
        "weather.py"
      ]
    }
  }
}
```

**Note**: Replace `/path/to/uv` with your actual `uv` installation path (e.g., `/Users/username/.local/bin/uv`) and `/path/to/img_gen` with the absolute path to this project directory.

## Usage

### Running the MCP Servers

#### Image Generation Server:
```bash
uv run image_generation.py
```

#### Weather Server:
```bash
uv run weather.py
```

### Image Generation

The `generate_image` tool accepts a text prompt and returns a generated image:

- **Tool**: `generate_image`
- **Parameters**:
  - `prompt` (string): A text description of the image you want to generate
- **Returns**: MCP Content objects containing the generated image in base64 format

### Weather Services

#### Get Weather Alerts
- **Tool**: `get_alerts`
- **Parameters**:
  - `state` (string): Two-letter US state code (e.g., "CA", "NY")
- **Returns**: Active weather alerts for the specified state

#### Get Weather Forecast
- **Tool**: `get_forecast`
- **Parameters**:
  - `latitude` (float): Latitude of the location (up to 4 decimal places recommended)
  - `longitude` (float): Longitude of the location (up to 4 decimal places recommended)
- **Returns**: Detailed weather forecast for the next 5 periods

## Project Structure

```
img_gen/
├── image_generation.py  # MCP server for image generation using Gemini API
├── weather.py           # MCP server for weather alerts and forecasts
├── main.py              # Basic entry point
├── pyproject.toml       # Project dependencies and configuration
├── uv.lock              # Locked dependency versions
└── README.md            # This file
```

## Image Processing

The image generation server includes automatic image optimization:

- **Max Dimension**: 1024 pixels (maintains aspect ratio)
- **JPEG Quality**: 85
- **Target File Size**: ~500 KB
- **Format**: Converts all images to JPEG for consistency

Images are automatically resized and compressed to reduce token usage while maintaining reasonable quality.

## Dependencies

Key dependencies include:
- `mcp[cli]` - Model Context Protocol framework
- `google-genai` - Google Gemini API client
- `pillow` - Image processing
- `httpx` - HTTP client for weather API

See `pyproject.toml` for the complete list of dependencies.

## Logging

Both servers include comprehensive logging:
- Logs are written to `stderr`
- Log levels: INFO, DEBUG, WARNING, ERROR
- Includes timestamps and module names

## Error Handling

- Image generation failures return error messages via MCP
- Weather API failures gracefully handle network issues
- Invalid inputs are validated and return appropriate error messages

## License

[Add your license here]

## Contributing

[Add contribution guidelines if applicable]

