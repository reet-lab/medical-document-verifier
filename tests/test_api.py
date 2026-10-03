"""Test suite for the Medical Document Verification API."""

import io
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services import ClassificationOutput, ImageValidationError
from app.schemas import VerificationStatus


@pytest.fixture
def client():
    """FastAPI test client with lifespan context."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def valid_jpeg_bytes():
    """Generate a valid JPEG image as bytes."""
    image = Image.new("RGB", (800, 1000), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def valid_png_bytes():
    """Generate a valid PNG image as bytes."""
    image = Image.new("RGB", (800, 1000), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def large_image_bytes():
    """Generate an image that exceeds dimension limits."""
    image = Image.new("RGB", (5000, 5000), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def tiny_image_bytes():
    """Generate an image smaller than minimum dimensions."""
    image = Image.new("RGB", (50, 50), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def corrupted_image_bytes():
    """Generate corrupted image data."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG header but invalid data


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test GET / returns healthy status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Medical Document Verification API" in data["message"]

    def test_health_endpoint(self, client):
        """Test GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_status_endpoint(self, client):
        """Test GET /api/v1/status returns service information."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "classifier_loaded" in data
        assert isinstance(data["classifier_loaded"], bool)
        assert "supported_formats" in data
        assert "JPEG" in data["supported_formats"]
        assert "PNG" in data["supported_formats"]


class TestDocumentVerification:
    """Tests for document verification endpoint."""

    def test_verify_valid_jpeg(self, client, valid_jpeg_bytes):
        """Test uploading a valid JPEG image."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("test.jpg", valid_jpeg_bytes, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "request_id" in data
        assert "status" in data
        assert data["status"] in ["classified", "needs_review", "unavailable"]
        assert "document_type" in data
        assert "confidence" in data["document_type"]
        assert "country" in data
        assert "evidence" in data
        assert isinstance(data["evidence"], list)
        assert "limitations" in data
        assert "image" in data

        # Check image metadata
        assert data["image"]["format"] == "JPEG"
        assert data["image"]["width"] == 800
        assert data["image"]["height"] == 1000
        assert data["image"]["mode"] == "RGB"

    def test_verify_valid_png(self, client, valid_png_bytes):
        """Test uploading a valid PNG image."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("test.png", valid_png_bytes, "image/png")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["image"]["format"] == "PNG"

    def test_reject_empty_file(self, client):
        """Test that empty files are rejected."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("empty.jpg", b"", "image/jpeg")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "empty" in data["detail"].lower()

    def test_reject_corrupted_image(self, client, corrupted_image_bytes):
        """Test that corrupted images are rejected."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("corrupted.jpg", corrupted_image_bytes, "image/jpeg")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_reject_oversized_dimensions(self, client, large_image_bytes):
        """Test that images exceeding dimension limits are rejected."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("large.jpg", large_image_bytes, "image/jpeg")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "exceed" in data["detail"].lower() or "large" in data["detail"].lower()

    def test_reject_tiny_image(self, client, tiny_image_bytes):
        """Test that images below minimum dimensions are rejected."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("tiny.jpg", tiny_image_bytes, "image/jpeg")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "small" in data["detail"].lower() or "minimum" in data["detail"].lower()

    def test_reject_unsupported_format(self, client):
        """Test that unsupported image formats are rejected."""
        # Create a GIF image
        image = Image.new("RGB", (800, 1000), color="white")
        buffer = io.BytesIO()
        image.save(buffer, format="GIF")
        buffer.seek(0)
        gif_bytes = buffer.getvalue()

        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("test.gif", gif_bytes, "image/gif")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "format" in data["detail"].lower()

    def test_mime_type_spoofing(self, client, valid_jpeg_bytes):
        """Test that MIME type is verified against actual file format."""
        # Send JPEG with PNG MIME type claim
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("fake.png", valid_jpeg_bytes, "image/png")}
        )
        # Should still succeed because we validate actual format, not claimed type
        # The actual format is JPEG which is allowed
        assert response.status_code == 200

    def test_baseline_returns_needs_review(self, client, valid_jpeg_bytes):
        """Test that baseline classifier returns needs_review status."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("test.jpg", valid_jpeg_bytes, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()

        # Baseline classifier should indicate uncertainty
        assert data["status"] == "needs_review"
        assert data["document_type"]["confidence"] == 0.0
        assert data["country"]["confidence"] == 0.0
        assert len(data["evidence"]) > 0

    def test_response_includes_limitations(self, client, valid_jpeg_bytes):
        """Test that response includes disclaimer about limitations."""
        response = client.post(
            "/api/v1/verify-document",
            files={"file": ("test.jpg", valid_jpeg_bytes, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "limitations" in data
        assert len(data["limitations"]) > 0
        # Check for key disclaimer
        limitations_text = " ".join(data["limitations"]).lower()
        assert "official" in limitations_text or "authenticity" in limitations_text

    def test_request_id_is_unique(self, client, valid_jpeg_bytes):
        """Test that each request gets a unique request_id."""
        response1 = client.post(
            "/api/v1/verify-document",
            files={"file": ("test1.jpg", valid_jpeg_bytes, "image/jpeg")}
        )
        response2 = client.post(
            "/api/v1/verify-document",
            files={"file": ("test2.jpg", valid_jpeg_bytes, "image/jpeg")}
        )
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["request_id"] != response2.json()["request_id"]


class TestImageValidation:
    """Tests for image validation logic."""

    def test_file_size_validation(self):
        """Test file size validation."""
        from app.services.image_processing import ImageValidator

        validator = ImageValidator()

        # Valid size
        validator.validate_file_size(1024 * 1024)  # 1MB

        # Empty file
        with pytest.raises(ImageValidationError, match="empty"):
            validator.validate_file_size(0)

        # Oversized file
        with pytest.raises(ImageValidationError, match="exceeds"):
            validator.validate_file_size(100 * 1024 * 1024)  # 100MB

    def test_dimension_validation(self):
        """Test image dimension validation."""
        from app.services.image_processing import ImageValidator

        validator = ImageValidator()

        # Valid dimensions
        valid_image = Image.new("RGB", (800, 1000))
        validator.validate_image_dimensions(valid_image)

        # Too small
        tiny_image = Image.new("RGB", (50, 50))
        with pytest.raises(ImageValidationError, match="small"):
            validator.validate_image_dimensions(tiny_image)

        # Too wide
        wide_image = Image.new("RGB", (10000, 100))
        with pytest.raises(ImageValidationError, match="width"):
            validator.validate_image_dimensions(wide_image)

        # Too tall
        tall_image = Image.new("RGB", (100, 10000))
        with pytest.raises(ImageValidationError, match="height"):
            validator.validate_image_dimensions(tall_image)


class TestClassifier:
    """Tests for classifier logic."""

    def test_baseline_classifier_available(self):
        """Test that baseline classifier reports as available."""
        from app.services.classifier import BaselineClassifier

        classifier = BaselineClassifier()
        assert classifier.is_available() is True
        assert classifier.get_version() is not None

    def test_baseline_classify_returns_needs_review(self):
        """Test that baseline classifier returns needs_review status."""
        from app.services.classifier import BaselineClassifier

        classifier = BaselineClassifier()
        test_image = Image.new("RGB", (800, 1000), color="white")

        result = classifier.classify(test_image)

        assert result.status == VerificationStatus.NEEDS_REVIEW
        assert result.document_type_confidence == 0.0
        assert result.country_confidence == 0.0
        assert len(result.evidence) > 0
        assert result.genuine_looking is None

    def test_classifier_factory(self):
        """Test classifier factory creates baseline instance."""
        from app.services.classifier import ClassifierFactory, BaselineClassifier

        classifier = ClassifierFactory.create_classifier()
        assert isinstance(classifier, BaselineClassifier)
        assert classifier.is_available()


class TestPreprocessing:
    """Tests for image preprocessing."""

    def test_preprocessor_resize(self):
        """Test that preprocessor resizes images correctly."""
        from app.services.image_processing import ImagePreprocessor

        preprocessor = ImagePreprocessor(target_size=(512, 512))

        # Large image
        large_image = Image.new("RGB", (2000, 3000))
        processed = preprocessor.preprocess(large_image)
        assert processed.size == (512, 512)
        assert processed.mode == "RGB"

        # Small image
        small_image = Image.new("RGB", (200, 300))
        processed = preprocessor.preprocess(small_image)
        assert processed.size == (512, 512)

    def test_preprocessor_mode_conversion(self):
        """Test that preprocessor converts to RGB."""
        from app.services.image_processing import ImagePreprocessor

        preprocessor = ImagePreprocessor(target_size=(512, 512))

        # RGBA image
        rgba_image = Image.new("RGBA", (800, 1000))
        processed = preprocessor.preprocess(rgba_image)
        assert processed.mode == "RGB"

        # Grayscale image
        gray_image = Image.new("L", (800, 1000))
        processed = preprocessor.preprocess(gray_image)
        assert processed.mode == "RGB"

    def test_extract_metadata(self):
        """Test metadata extraction."""
        from app.services.image_processing import ImagePreprocessor

        preprocessor = ImagePreprocessor()
        test_image = Image.new("RGB", (800, 1000))
        test_image.format = "JPEG"

        metadata = preprocessor.extract_metadata(test_image, file_size=12345)

        assert metadata["format"] == "JPEG"
        assert metadata["width"] == 800
        assert metadata["height"] == 1000
        assert metadata["mode"] == "RGB"
        assert metadata["size_bytes"] == 12345
