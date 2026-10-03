"""Image validation and preprocessing utilities."""

import io
from pathlib import Path
from typing import BinaryIO, Optional

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings


class ImageValidationError(Exception):
    """Raised when image validation fails."""

    pass


class ImageValidator:
    """Validates uploaded images for security and format compliance."""

    ALLOWED_FORMATS = {"JPEG", "PNG"}
    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}

    def __init__(self):
        self.settings = get_settings()

    def validate_file_size(self, file_size: int) -> None:
        """
        Validate that file size is within acceptable limits.

        Args:
            file_size: File size in bytes

        Raises:
            ImageValidationError: If file size exceeds maximum
        """
        max_size = self.settings.max_file_size_bytes
        if file_size > max_size:
            max_mb = self.settings.max_file_size_mb
            raise ImageValidationError(
                f"File size exceeds maximum allowed size of {max_mb}MB"
            )

        if file_size == 0:
            raise ImageValidationError("File is empty")

    def validate_image_format(self, image: Image.Image) -> None:
        """
        Validate that image format is supported.

        Args:
            image: Pillow Image object

        Raises:
            ImageValidationError: If format is not supported
        """
        if image.format not in self.ALLOWED_FORMATS:
            raise ImageValidationError(
                f"Unsupported image format: {image.format}. "
                f"Allowed formats: {', '.join(self.ALLOWED_FORMATS)}"
            )

    def validate_image_dimensions(self, image: Image.Image) -> None:
        """
        Validate that image dimensions are within acceptable limits.

        Args:
            image: Pillow Image object

        Raises:
            ImageValidationError: If dimensions exceed limits
        """
        width, height = image.size

        if width > self.settings.max_image_width:
            raise ImageValidationError(
                f"Image width {width}px exceeds maximum {self.settings.max_image_width}px"
            )

        if height > self.settings.max_image_height:
            raise ImageValidationError(
                f"Image height {height}px exceeds maximum {self.settings.max_image_height}px"
            )

        total_pixels = width * height
        if total_pixels > self.settings.max_image_pixels:
            raise ImageValidationError(
                f"Image resolution {total_pixels} pixels exceeds maximum "
                f"{self.settings.max_image_pixels} pixels"
            )

        if width < 100 or height < 100:
            raise ImageValidationError(
                "Image dimensions too small. Minimum 100x100 pixels required."
            )

    def load_and_validate(
        self, file_data: bytes, filename: Optional[str] = None
    ) -> Image.Image:
        """
        Load image from bytes and validate format, dimensions, and integrity.

        This method:
        1. Validates file size
        2. Attempts to load the image (verifies it's a real image)
        3. Validates the actual format against allowed formats
        4. Validates dimensions
        5. Returns a freshly loaded image ready for processing

        Args:
            file_data: Raw image file bytes
            filename: Optional filename (for error messages only, not trusted)

        Returns:
            Validated Pillow Image object in RGB mode

        Raises:
            ImageValidationError: If validation fails at any step
        """
        # Validate file size
        file_size = len(file_data)
        self.validate_file_size(file_size)

        # Attempt to load image
        try:
            # First pass: verify it's a valid image
            with Image.open(io.BytesIO(file_data)) as img:
                # Load image header and verify integrity
                img.load()

                # Validate format (actual format, not client-claimed)
                self.validate_image_format(img)

                # Validate dimensions
                self.validate_image_dimensions(img)

                # Store format for after we reload
                image_format = img.format

            # Second pass: reload for actual use
            # (after verify(), the image object can't be used reliably)
            image = Image.open(io.BytesIO(file_data))
            image.load()

            # Convert to RGB if needed (handles RGBA, L, etc.)
            if image.mode != "RGB":
                image = image.convert("RGB")

            return image

        except UnidentifiedImageError as e:
            raise ImageValidationError(
                "File is not a valid image or format cannot be identified"
            ) from e
        except OSError as e:
            # Pillow raises OSError for truncated/corrupted images
            raise ImageValidationError(
                f"Image file is corrupted or truncated: {str(e)}"
            ) from e
        except Exception as e:
            raise ImageValidationError(
                f"Failed to process image: {str(e)}"
            ) from e


class ImagePreprocessor:
    """Preprocesses images for classification."""

    def __init__(self, target_size: tuple[int, int] = (512, 512)):
        """
        Initialize preprocessor.

        Args:
            target_size: Target (width, height) for resized images
        """
        self.target_size = target_size

    def preprocess(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for classification.

        - Resizes while maintaining aspect ratio
        - Pads to square if needed
        - Normalizes to RGB

        Args:
            image: Input PIL Image

        Returns:
            Preprocessed PIL Image
        """
        # Ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Resize maintaining aspect ratio
        image.thumbnail(self.target_size, Image.Resampling.LANCZOS)

        # Pad to square if needed
        if image.size != self.target_size:
            padded = Image.new("RGB", self.target_size, (255, 255, 255))
            offset = (
                (self.target_size[0] - image.size[0]) // 2,
                (self.target_size[1] - image.size[1]) // 2,
            )
            padded.paste(image, offset)
            image = padded

        return image

    def extract_metadata(self, image: Image.Image, file_size: Optional[int] = None) -> dict:
        """
        Extract safe metadata from image.

        Args:
            image: PIL Image object
            file_size: Optional file size in bytes

        Returns:
            Dictionary with image metadata
        """
        return {
            "format": image.format or "UNKNOWN",
            "width": image.size[0],
            "height": image.size[1],
            "mode": image.mode,
            "size_bytes": file_size,
        }
