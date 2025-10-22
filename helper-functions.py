try:
    from PIL import Image
except ImportError:
    print("Pillow library not found. Please install it using: pip install Pillow")
    # Or handle the absence of the library in another way
    # raise an error instead of printing an error message
    raise ImportError("Pillow library not found. Please install it using: pip install Pillow")

import io

def crop_and_resize_image(target_x, target_y, image_bytes):
    """
    Crops and resizes an image to the target resolution while maintaining aspect ratio.

    Args:
        target_x (int): The target width of the image.
        target_y (int): The target height of the image.
        image_bytes (bytes): The byte array representing the image.

    Returns:
        bytes: The processed image as a byte array.
    """
    # Open the image from the byte array
    image = Image.open(io.BytesIO(image_bytes))

    # Calculate the target aspect ratio
    target_aspect = target_x / target_y

    # Calculate the current aspect ratio
    current_aspect = image.width / image.height

    # Crop the image to the target aspect ratio
    if current_aspect > target_aspect:
        # Image is wider than the target aspect ratio, so crop the width
        new_width = int(target_aspect * image.height)
        left = (image.width - new_width) / 2
        top = 0
        right = left + new_width
        bottom = image.height
        cropped_image = image.crop((left, top, right, bottom))
    else:
        # Image is taller than or equal to the target aspect ratio, so crop the height
        new_height = int(image.width / target_aspect)
        left = 0
        top = (image.height - new_height) / 2
        right = image.width
        bottom = top + new_height
        cropped_image = image.crop((left, top, right, bottom))

    # Scale the cropped image to the target resolution
    resized_image = cropped_image.resize((target_x, target_y))

    # Save the processed image to a byte array
    output_buffer = io.BytesIO()
    resized_image.save(output_buffer, format='PNG') # Use a consistent format for testing
    return output_buffer.getvalue()
