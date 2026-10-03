"""Pydantic schemas for API request and response models."""

from enum import Enum
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    """Supported document type classifications."""

    MEDICAL_REGISTRATION_CERTIFICATE = "medical_registration_certificate"
    MEDICAL_COUNCIL_REGISTRATION = "medical_council_registration"
    PROVISIONAL_REGISTRATION = "provisional_registration"
    UNKNOWN = "unknown"


class Country(str, Enum):
    """Supported country/jurisdiction classifications."""

    INDIA = "India"
    UNKNOWN = "unknown"


class ClassificationResult(BaseModel):
    """Classification result with label and confidence."""

    label: str = Field(
        ...,
        description="The predicted classification label",
        examples=["medical_registration_certificate", "India"]
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )


class ImageMetadata(BaseModel):
    """Metadata about the uploaded image."""

    format: str = Field(..., description="Image format (JPEG, PNG, etc.)")
    width: int = Field(..., ge=1, description="Image width in pixels")
    height: int = Field(..., ge=1, description="Image height in pixels")
    mode: str = Field(
        ...,
        description="Image color mode (RGB, RGBA, L, etc.)"
    )
    size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="File size in bytes"
    )


class VerificationStatus(str, Enum):
    """Overall verification status."""

    CLASSIFIED = "classified"
    NEEDS_REVIEW = "needs_review"
    UNAVAILABLE = "unavailable"


class VerificationResponse(BaseModel):
    """Response model for document verification endpoint."""

    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this verification request"
    )
    status: VerificationStatus = Field(
        ...,
        description=(
            "Overall status: 'classified' (confident prediction), "
            "'needs_review' (uncertain or out-of-distribution), "
            "'unavailable' (classifier not loaded or error)"
        )
    )
    genuine_looking: Optional[bool] = Field(
        None,
        description=(
            "Whether the image appears consistent with a medical registration document. "
            "This does NOT verify authenticity or registry validity."
        )
    )
    document_type: ClassificationResult = Field(
        ...,
        description="Predicted document type and confidence"
    )
    country: ClassificationResult = Field(
        ...,
        description="Predicted country/jurisdiction and confidence"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Brief explanations of visual signals used for classification. "
            "Does not include sensitive OCR text unless necessary."
        )
    )
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Classification does not verify registration against an official authority.",
            "This service estimates document appearance only, not authenticity or validity."
        ],
        description="Important disclaimers about what this service does NOT do"
    )
    image: ImageMetadata = Field(
        ...,
        description="Technical metadata about the uploaded image"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "classified",
                    "genuine_looking": True,
                    "document_type": {
                        "label": "medical_registration_certificate",
                        "confidence": 0.85
                    },
                    "country": {
                        "label": "India",
                        "confidence": 0.78
                    },
                    "evidence": [
                        "Document has structured layout typical of official certificates",
                        "Contains registration number format patterns"
                    ],
                    "limitations": [
                        "Classification does not verify registration against an official authority.",
                        "This service estimates document appearance only, not authenticity or validity."
                    ],
                    "image": {
                        "format": "JPEG",
                        "width": 1200,
                        "height": 1600,
                        "mode": "RGB",
                        "size_bytes": 245678
                    }
                }
            ]
        }
    }


class ErrorDetail(BaseModel):
    """Error response model."""

    detail: str = Field(..., description="Human-readable error message")
    request_id: Optional[str] = Field(
        None,
        description="Request ID if available"
    )
    error_code: Optional[str] = Field(
        None,
        description="Machine-readable error code"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall service health"
    )
    message: str = Field(..., description="Human-readable status message")


class StatusResponse(BaseModel):
    """Service status and classifier readiness."""

    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    classifier_loaded: bool = Field(
        ...,
        description="Whether the classifier model is loaded and ready"
    )
    model_version: Optional[str] = Field(
        None,
        description="Active model version identifier"
    )
    supported_formats: list[str] = Field(
        default=["JPEG", "PNG"],
        description="Supported image formats"
    )
