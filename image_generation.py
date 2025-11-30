from typing import Any
from mcp.server.fastmcp import FastMCP
from mcp import types as mcp_types
import base64
import mimetypes
import logging
import sys
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("image_generation")

# Initialize FastMCP server
mcp = FastMCP("image_generation")

# Image compression settings
MAX_IMAGE_DIMENSION = 1024  # Maximum width or height in pixels
JPEG_QUALITY = 85  # JPEG quality (1-100, higher = better quality but larger file)
MAX_FILE_SIZE_KB = 500  # Target max file size in KB (approximate)

def resize_and_compress_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """
    Resize and compress an image to reduce file size.
    
    Args:
        image_bytes: Raw image bytes
        mime_type: Original MIME type of the image
        
    Returns:
        Tuple of (compressed_image_bytes, new_mime_type)
    """
    try:
        logger.debug(f"Starting image compression. Original size: {len(image_bytes)} bytes, type: {mime_type}")
        
        # Open image from bytes
        image = Image.open(BytesIO(image_bytes))
        original_size = image.size
        logger.debug(f"Original image dimensions: {original_size[0]}x{original_size[1]}")
        
        # Resize if needed (maintain aspect ratio)
        if image.width > MAX_IMAGE_DIMENSION or image.height > MAX_IMAGE_DIMENSION:
            image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {original_size} to {image.size}")
        
        # Convert to RGB if needed (JPEG doesn't support alpha channel)
        original_mode = image.mode
        if image.mode in ('RGBA', 'LA'):
            # Create a white background and paste the image with alpha channel
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'RGBA':
                rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            else:  # LA mode
                rgb_image.paste(image.convert('RGBA'), mask=image.split()[1])
            image = rgb_image
            logger.debug(f"Converted image from {original_mode} to RGB for JPEG compression")
        elif image.mode != 'RGB':
            # Convert any other mode to RGB
            image = image.convert('RGB')
            logger.debug(f"Converted image from {original_mode} to RGB for JPEG compression")
        
        # Compress as JPEG
        output_buffer = BytesIO()
        image.save(
            output_buffer,
            format='JPEG',
            quality=JPEG_QUALITY,
            optimize=True
        )
        compressed_bytes = output_buffer.getvalue()
        new_size = len(compressed_bytes)
        compression_ratio = (1 - new_size / len(image_bytes)) * 100
        
        logger.info(f"Image compression complete. New size: {new_size} bytes "
                   f"({new_size / 1024:.1f} KB), compression ratio: {compression_ratio:.1f}%")
        
        return compressed_bytes, "image/jpeg"
        
    except Exception as e:
        logger.warning(f"Failed to compress image: {str(e)}. Returning original.")
        return image_bytes, mime_type

# def save_binary_file(file_name, data):
#     f = open(file_name, "wb")
#     f.write(data)
#     f.close()
#     print(f"File saved to to: {file_name}")

def generate(prompt: str) -> dict[str, Any] | None:
    logger.info(f"Starting image generation with prompt: {prompt[:100]}...")
    
    API_KEY="ENTER_YOUR_API_KEY" 
    # Validate API key
    if not API_KEY:
        error_msg = "GEMINI_API_KEY environment variable is not set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    logger.debug("API key found and validated")
    
    try:
        logger.info("Initializing Gemini client")
        client = genai.Client(api_key=API_KEY)
        logger.debug("Gemini client initialized successfully")

        model = "gemini-2.5-flash-image"
        logger.info(f"Using model: {model}")
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        logger.debug(f"Content prepared with prompt length: {len(prompt)}")
        
        generate_content_config = types.GenerateContentConfig(
            response_modalities=[
                "IMAGE",
                "TEXT",
            ],
        )
        logger.debug("Content generation config set with IMAGE and TEXT modalities")

        logger.info("Starting content generation stream")
        chunk_count = 0
        text_parts = []
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            chunk_count += 1
            logger.debug(f"Received chunk #{chunk_count}")
            
            if (
                chunk.candidates is None
                or len(chunk.candidates) == 0
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                logger.warning(f"Chunk #{chunk_count} has missing candidates/content/parts, skipping")
                continue
                
            parts = chunk.candidates[0].content.parts
            logger.debug(f"Chunk #{chunk_count} has {len(parts)} part(s)")
            
            for part_idx, part in enumerate(parts):
                if part.inline_data and part.inline_data.data:
                    inline_data = part.inline_data
                    data_buffer = inline_data.data
                    mime_type = inline_data.mime_type
                    original_size = len(data_buffer)
                    logger.info(f"Found image data in chunk #{chunk_count}, part #{part_idx}: "
                              f"mime_type={mime_type}, size={original_size} bytes ({original_size / 1024:.1f} KB)")
                    
                    # Resize and compress the image to reduce token usage
                    compressed_buffer, compressed_mime_type = resize_and_compress_image(data_buffer, mime_type)
                    compressed_size = len(compressed_buffer)
                    
                    logger.info(f"Image processed: {original_size / 1024:.1f} KB -> {compressed_size / 1024:.1f} KB")
                    
                    # Encode binary data to base64 for JSON serialization
                    base64_data = base64.b64encode(compressed_buffer).decode('utf-8')
                    logger.debug(f"Encoded image data to base64, length: {len(base64_data)}")
                    logger.info("Image generation completed successfully")
                    
                    return {
                        "image_data": base64_data,
                        "mime_type": compressed_mime_type,
                        "size_bytes": compressed_size
                    }
                elif hasattr(part, 'text') and part.text:
                    text_content = part.text
                    text_parts.append(text_content)
                    logger.debug(f"Received text part in chunk #{chunk_count}: {text_content[:100]}...")
        
        # If we reach here, no image was found
        if text_parts:
            combined_text = "".join(text_parts)
            logger.warning(f"No image data found in response. Received text: {combined_text[:200]}...")
        else:
            logger.warning(f"Processed {chunk_count} chunks but found no image data or text content")
        
        logger.error("Image generation failed: No image data returned from API")
        return None
        
    except Exception as e:
        logger.exception(f"Error during image generation: {str(e)}")
        raise

@mcp.tool()
async def generate_image(prompt: str) -> list[mcp_types.Content]:
    """Create images based on the prompt
    
    Args:
        prompt: A prompt to generate the image using image generation model
    
    Returns:
        A list of MCP Content objects containing the generated image
    """
    logger.info(f"generate_image tool called with prompt length: {len(prompt)}")
    try:
        result = generate(prompt)
        if result is None:
            logger.warning("generate_image returned None - no image data was generated")
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: No image data was generated from the prompt."
                )
            ]
        elif isinstance(result, dict) and "image_data" in result:
            base64_data = result.get("image_data")
            mime_type = result.get("mime_type", "image/png")
            size_bytes = result.get("size_bytes", 0)
            
            logger.info(f"generate_image completed successfully, returning image with "
                       f"mime_type={mime_type}, size={size_bytes} bytes")
            
            # Return MCP content types for proper image rendering
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Generated image ({mime_type}, {size_bytes} bytes):"
                ),
                mcp_types.ImageContent(
                    type="image",
                    data=base64_data,
                    mimeType=mime_type
                )
            ]
        else:
            logger.warning(f"Unexpected result type: {type(result)}")
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: Unexpected result format. Got type: {type(result)}"
                )
            ]
    except Exception as e:
        logger.exception(f"Error in generate_image tool: {str(e)}")
        return [
            mcp_types.TextContent(
                type="text",
                text=f"Error generating image: {str(e)}"
            )
        ]

def main():
    """Initialize and run the MCP server"""
    logger.info("Starting image_generation MCP server")
    logger.info("Server will run on stdio transport")
    try:
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error in server: {str(e)}")
        raise

if __name__ == "__main__":
    main()
