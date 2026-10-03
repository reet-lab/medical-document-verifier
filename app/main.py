"""Main FastAPI application."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.schemas import (
    ErrorDetail,
    HealthResponse,
    ImageMetadata,
    StatusResponse,
    VerificationResponse,
    VerificationStatus,
)
from app.services import (
    ClassificationOutput,
    ClassifierFactory,
    DocumentClassifier,
    ImagePreprocessor,
    ImageValidationError,
    ImageValidator,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
classifier: Optional[DocumentClassifier] = None
validator: Optional[ImageValidator] = None
preprocessor: Optional[ImagePreprocessor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    # Startup
    global classifier, validator, preprocessor
    settings = get_settings()

    logger.info("Starting Medical Document Verification API")
    logger.info(f"Log level: {settings.log_level}")

    # Initialize services
    validator = ImageValidator()
    preprocessor = ImagePreprocessor(target_size=(512, 512))

    # Initialize classifier
    try:
        classifier = ClassifierFactory.create_classifier(
            model_path=settings.model_path,
            version=settings.model_version
        )
        if classifier.is_available():
            logger.info(f"Classifier loaded: {classifier.get_version()}")
        else:
            logger.warning("Classifier unavailable")
    except Exception as e:
        logger.error(f"Failed to initialize classifier: {e}")
        classifier = None

    logger.info("Application startup complete")

    yield  # Application runs

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_credentials,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Middleware for request logging and timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "unknown")

    # Don't log sensitive data
    logger.info(
        f"Request started: {request.method} {request.url.path} "
        f"(request_id={request_id})"
    )

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"status={response.status_code} duration={duration:.3f}s"
    )

    return response


@app.exception_handler(ImageValidationError)
async def validation_error_handler(request: Request, exc: ImageValidationError):
    """Handle image validation errors with appropriate HTTP responses."""
    return JSONResponse(
        status_code=400,
        content=ErrorDetail(
            detail=str(exc),
            error_code="VALIDATION_ERROR"
        ).model_dump()
    )


@app.get("/", response_model=HealthResponse, tags=["Health"])
def root():
    """
    Root endpoint - basic health check.

    Returns a simple status message indicating the API is running.
    """
    return HealthResponse(
        status="healthy",
        message="Medical Document Verification API is running"
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Health check endpoint.

    Returns the overall health status of the service.
    """
    return HealthResponse(
        status="healthy",
        message="Service is operational"
    )


@app.get("/api/v1/status", response_model=StatusResponse, tags=["Status"])
def get_status():
    """
    Get service status and classifier readiness.

    Returns information about:
    - Service version
    - Whether the classifier is loaded
    - Active model version
    - Supported image formats
    """
    settings = get_settings()

    return StatusResponse(
        service=settings.api_title,
        version=settings.api_version,
        classifier_loaded=classifier is not None and classifier.is_available(),
        model_version=classifier.get_version() if classifier else None,
        supported_formats=["JPEG", "PNG"]
    )


@app.post("/api/v1/verify-document", response_model=VerificationResponse, tags=["Verification"])
async def verify_document(file: UploadFile = File(...)):
    """
    Verify a medical registration document image.

    Accepts an uploaded JPEG or PNG image and returns:
    - Classification status (classified, needs_review, or unavailable)
    - Document type and confidence
    - Country/jurisdiction and confidence
    - Evidence of visible signals
    - Important limitations

    **Important:** This endpoint classifies document appearance only.
    It does NOT:
    - Verify registration against official registries
    - Confirm document authenticity or validity
    - Provide legal verification

    Args:
        file: Uploaded image file (JPEG or PNG)

    Returns:
        VerificationResponse with classification results

    Raises:
        HTTPException 400: Invalid file format, corrupted image, or size limits exceeded
        HTTPException 503: Classifier unavailable
    """
    # Check classifier availability
    if classifier is None or not classifier.is_available():
        raise HTTPException(
            status_code=503,
            detail="Document classifier is currently unavailable. Please try again later."
        )

    # Read file data
    try:
        file_data = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to read uploaded file"
        )

    # Validate and load image
    try:
        image = validator.load_and_validate(file_data, filename=file.filename)
    except ImageValidationError as e:
        # Already logged by exception handler
        raise

    # Extract metadata before preprocessing
    metadata = preprocessor.extract_metadata(image, file_size=len(file_data))

    # Preprocess image
    try:
        processed_image = preprocessor.preprocess(image)
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to preprocess image"
        )

    # Classify document
    try:
        result: ClassificationOutput = classifier.classify(processed_image)
    except Exception as e:
        logger.error(f"Classification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Classification process failed"
        )

    # Build response
    response = VerificationResponse(
        status=result.status,
        genuine_looking=result.genuine_looking,
        document_type={
            "label": result.document_type,
            "confidence": result.document_type_confidence
        },
        country={
            "label": result.country,
            "confidence": result.country_confidence
        },
        evidence=result.evidence,
        image=ImageMetadata(**metadata)
    )

    return response