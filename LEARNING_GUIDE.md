# Learning Guide: Medical Document Verification API

This guide walks you through the architecture, code structure, and request flow so you can confidently maintain and extend this project.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Request Flow: End-to-End](#request-flow-end-to-end)
3. [File-by-File Guide](#file-by-file-guide)
4. [Key Concepts Explained](#key-concepts-explained)
5. [How to Extend the System](#how-to-extend-the-system)
6. [Confidence Scores: What They Mean](#confidence-scores-what-they-mean)
7. [Common Modification Scenarios](#common-modification-scenarios)
8. [Comprehension Questions](#comprehension-questions)

---

## Architecture Overview

The application follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│         FastAPI Routes (app/main.py)            │  ← HTTP endpoints
├─────────────────────────────────────────────────┤
│           Pydantic Schemas (schemas/)           │  ← Request/response models
├─────────────────────────────────────────────────┤
│              Services Layer                     │
│  ┌──────────────────┐  ┌───────────────────┐  │
│  │ Image Validation │  │   Classifier      │  │  ← Business logic
│  │  & Preprocessing │  │   Interface       │  │
│  └──────────────────┘  └───────────────────┘  │
├─────────────────────────────────────────────────┤
│       Configuration (core/config.py)            │  ← Settings management
└─────────────────────────────────────────────────┘
```

**Why this structure?**

- **Routes** handle HTTP concerns (parsing uploads, error codes, JSON serialization)
- **Schemas** define the contract (what requests/responses look like)
- **Services** contain reusable logic (validate any image, classify any image)
- **Configuration** centralizes all settings in one place

This means you can change validation rules without touching the routes, or swap the classifier without changing the API contract.

---

## Request Flow: End-to-End

Let's trace what happens when someone uploads an image to `/api/v1/verify-document`:

### 1. HTTP Request Arrives (main.py:208)

```python
@app.post("/api/v1/verify-document", ...)
async def verify_document(file: UploadFile = File(...)):
```

FastAPI automatically:
- Parses the multipart form data
- Creates an `UploadFile` object with the uploaded file
- Validates that a file was provided (the `...` means required)

### 2. Classifier Availability Check (main.py:232)

```python
if classifier is None or not classifier.is_available():
    raise HTTPException(status_code=503, ...)
```

Before doing any work, we check if the classifier is ready. The `classifier` is a global variable initialized during application startup in the `lifespan` function.

**Why check here?** If the service can't classify, we should fail fast rather than waste time validating the image.

### 3. Read File Data (main.py:237)

```python
file_data = await file.read()
```

The `await` keyword means this is asynchronous - the server can handle other requests while waiting for the file upload to complete.

We get raw bytes. We don't trust anything the client claimed (filename, content type, etc.) yet.

### 4. Validate and Load Image (main.py:244)

```python
image = validator.load_and_validate(file_data, filename=file.filename)
```

This is where security happens. Inside `ImageValidator.load_and_validate`:

**Step 4a: File Size Check** (image_processing.py:53)
```python
def validate_file_size(self, file_size: int) -> None:
    if file_size > max_size:
        raise ImageValidationError(...)
    if file_size == 0:
        raise ImageValidationError("File is empty")
```

**Step 4b: Load and Verify Format** (image_processing.py:111)
```python
with Image.open(io.BytesIO(file_data)) as img:
    img.load()  # Actually read the image data
    self.validate_image_format(img)  # Check it's JPEG or PNG
    self.validate_image_dimensions(img)  # Check size limits
```

**Important Pillow quirk:** After calling `img.verify()`, you can't use that image object anymore. That's why we load it twice - once to verify, once to actually use.

**Step 4c: Reload for Use** (image_processing.py:121)
```python
image = Image.open(io.BytesIO(file_data))
image.load()
if image.mode != "RGB":
    image = image.convert("RGB")
```

We convert everything to RGB so the classifier always gets consistent input (whether the upload was JPEG, PNG, RGBA, grayscale, etc.).

### 5. Extract Metadata (main.py:248)

```python
metadata = preprocessor.extract_metadata(image, file_size=len(file_data))
```

We capture the original image properties (format, dimensions, size) before preprocessing changes them. This goes in the response so the caller knows what we received.

### 6. Preprocess Image (main.py:252)

```python
processed_image = preprocessor.preprocess(image)
```

Inside `ImagePreprocessor.preprocess` (image_processing.py:158):

1. **Ensure RGB mode** (already done, but defensive)
2. **Resize maintaining aspect ratio** using `thumbnail()` - shrinks large images to 512x512 max
3. **Pad to square** - adds white borders if needed so all images are exactly 512x512

**Why square?** Many ML models expect fixed-size square inputs. By standardizing here, we can swap in different classifiers later without changing the preprocessing.

### 7. Classify Document (main.py:261)

```python
result: ClassificationOutput = classifier.classify(processed_image)
```

This calls the classifier's `classify` method. Right now that's `BaselineClassifier.classify` (classifier.py:81), which:

1. Calculates basic features (aspect ratio, resolution)
2. Generates evidence strings describing what it sees
3. Returns `status=needs_review` with 0.0 confidence

When you add a trained model, you'll implement a new classifier class that:
1. Runs the image through a neural network
2. Gets probability scores for each document type and country
3. Returns those scores as confidence values

The beauty: **the route code doesn't change**. It just calls `classify()` and gets back a `ClassificationOutput`.

### 8. Build Response (main.py:270)

```python
response = VerificationResponse(
    status=result.status,
    genuine_looking=result.genuine_looking,
    document_type={"label": result.document_type, "confidence": ...},
    ...
)
```

Pydantic validates the response structure and serializes it to JSON automatically.

### 9. Return to Client

FastAPI sends the JSON response with status code 200. The middleware logs the request duration.

---

## File-by-File Guide

### Core Files

#### `app/main.py` (278 lines)
**Responsibility:** HTTP layer - routes, middleware, error handling, application lifecycle.

**Key functions:**
- `lifespan()` (line 44): Initializes services on startup, cleans up on shutdown
- `verify_document()` (line 175): Main verification endpoint
- `log_requests()` (line 104): Middleware that logs every request with timing
- `validation_error_handler()` (line 128): Converts `ImageValidationError` exceptions to HTTP 400 responses

**Important pattern:** Global service instances (`classifier`, `validator`, `preprocessor`) are initialized once in `lifespan`, then reused for all requests. This is efficient - we don't reload the model for every upload.

#### `app/core/config.py` (122 lines)
**Responsibility:** Configuration management using environment variables.

**How it works:**
- `Settings` class defines all configuration with types and defaults
- `pydantic_settings` loads values from environment variables or `.env` file
- `get_settings()` is cached (via `@lru_cache`) so we read the environment once

**Example:** To change the max upload size, set `MAX_FILE_SIZE_MB=20` in `.env`. The `max_file_size_bytes` property automatically converts MB to bytes.

**Design choice:** Using Pydantic for config means:
- Type validation (can't accidentally set `port="abc"`)
- Clear error messages if required settings are missing
- Auto-generated documentation of what settings exist

#### `app/schemas/__init__.py` (172 lines)
**Responsibility:** Pydantic models defining API contracts.

**Key models:**
- `VerificationResponse` (line 52): What `/api/v1/verify-document` returns
- `ClassificationResult` (line 17): A label + confidence pair
- `ImageMetadata` (line 31): Technical image properties
- `ErrorDetail` (line 102): Structured error responses

**Why use Pydantic?**
- Automatic validation (can't return a negative confidence)
- Automatic JSON serialization
- OpenAPI docs generation (the `/docs` page reads these models)
- Type safety (your IDE can autocomplete field names)

**Example:** The `json_schema_extra` in `VerificationResponse` provides the example shown in API docs.

### Service Layer

#### `app/services/image_processing.py` (193 lines)
**Responsibility:** Image validation and preprocessing.

**Key classes:**

**`ImageValidator` (line 17):**
- `load_and_validate()` (line 80): Main entry point - validates everything and returns a PIL Image
- `validate_file_size()` (line 25)
- `validate_image_format()` (line 42)
- `validate_image_dimensions()` (line 57)

**Security design:**
- Never trust client-supplied content type - we load the image and check its actual format
- Never trust filename - we don't use it for anything except error messages
- Limits at multiple levels: file size, width, height, total pixels

**`ImagePreprocessor` (line 137):**
- `preprocess()` (line 150): Resize and normalize images for classification
- `extract_metadata()` (line 178): Get safe metadata for responses

**Why separate validation from preprocessing?** Validation rejects bad input. Preprocessing transforms good input. They have different concerns.

#### `app/services/classifier.py` (163 lines)
**Responsibility:** Document classification logic.

**Key classes:**

**`DocumentClassifier` (line 21):** Abstract base class defining the interface.
- `classify()`: Must return a `ClassificationOutput`
- `is_available()`: Is the classifier ready?
- `get_version()`: What version is loaded?

**Why an abstract class?** This is the **extension point**. When you add a trained model, you implement this interface. The rest of the code doesn't change.

**`BaselineClassifier` (line 46):** Current implementation.
- Honest about limitations - returns `needs_review`, not fake predictions
- Extracts basic features (aspect ratio, resolution) as examples
- Always available (no model file required)

**`ClassifierFactory` (line 144):** Creates classifier instances.
- Currently always returns `BaselineClassifier`
- Future: Check if trained model exists, load it, fall back to baseline

**Design pattern:** This is the **Strategy pattern** - multiple implementations of the same interface, swappable at runtime.

---

## Key Concepts Explained

### 1. Why async/await?

```python
async def verify_document(file: UploadFile = File(...)):
    file_data = await file.read()
```

`async` and `await` allow the server to handle multiple requests concurrently. While one request is waiting for a file upload, another can be processing an image. This makes the server more efficient under load.

**Rule of thumb:** Use `async def` for route handlers. Use `await` for I/O operations (reading files, database queries, external API calls).

### 2. Dependency Injection with FastAPI

```python
from app.core.config import get_settings

settings = get_settings()  # Called once due to @lru_cache
```

Instead of hardcoding configuration, we inject it. The `@lru_cache` decorator ensures `get_settings()` returns the same instance every time (singleton pattern).

### 3. Middleware

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Code before
    response = await call_next(request)
    # Code after
    return response
```

Middleware wraps every request. It's like a filter pipeline. Our logging middleware times every request without the route handlers needing to know.

### 4. Context Managers and Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
```

This ensures services are initialized before the first request and cleaned up when the server stops. It's like `try/finally` but for the application lifecycle.

### 5. Type Hints

```python
def load_and_validate(self, file_data: bytes, filename: Optional[str] = None) -> Image.Image:
```

- `file_data: bytes` - parameter type
- `filename: Optional[str] = None` - optional parameter (can be `None`)
- `-> Image.Image` - return type

Type hints help your IDE catch bugs before you run the code and make the code self-documenting.

---

## How to Extend the System

### Scenario 1: Add a Trained Classifier

**Step 1:** Train your model and save it (e.g., `models/trained_model.pkl`)

**Step 2:** Create a new classifier class in `app/services/classifier.py`:

```python
import pickle
from pathlib import Path

class TrainedClassifier(DocumentClassifier):
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)
        
        self.version = f"trained-{self.model_path.stem}"
    
    def classify(self, image: Image.Image) -> ClassificationOutput:
        # Convert image to numpy array
        import numpy as np
        img_array = np.array(image) / 255.0  # Normalize to [0, 1]
        
        # Run inference
        predictions = self.model.predict(img_array[np.newaxis, ...])
        
        # Extract predictions (adjust to your model's output)
        doc_type_probs = predictions["document_type"]
        country_probs = predictions["country"]
        
        # Get top predictions
        doc_type_idx = np.argmax(doc_type_probs)
        doc_type_conf = float(doc_type_probs[doc_type_idx])
        
        country_idx = np.argmax(country_probs)
        country_conf = float(country_probs[country_idx])
        
        # Map indices to labels (define these based on your training)
        DOC_TYPES = ["medical_registration_certificate", "medical_council_registration", ...]
        COUNTRIES = ["India", "USA", ...]
        
        # Determine status based on confidence
        status = (
            VerificationStatus.CLASSIFIED
            if doc_type_conf > 0.7 and country_conf > 0.7
            else VerificationStatus.NEEDS_REVIEW
        )
        
        return ClassificationOutput(
            status=status,
            genuine_looking=True if doc_type_conf > 0.7 else None,
            document_type=DOC_TYPES[doc_type_idx],
            document_type_confidence=doc_type_conf,
            country=COUNTRIES[country_idx],
            country_confidence=country_conf,
            evidence=[
                f"Document type prediction confidence: {doc_type_conf:.2f}",
                f"Country prediction confidence: {country_conf:.2f}"
            ]
        )
    
    def is_available(self) -> bool:
        return self.model is not None
    
    def get_version(self) -> str:
        return self.version
```

**Step 3:** Update `ClassifierFactory.create_classifier()`:

```python
@staticmethod
def create_classifier(model_path: Optional[str] = None, version: Optional[str] = None) -> DocumentClassifier:
    if model_path and Path(model_path).exists():
        try:
            return TrainedClassifier(model_path)
        except Exception as e:
            logger.error(f"Failed to load trained model: {e}")
            logger.info("Falling back to baseline classifier")
    
    return BaselineClassifier(version=version or "baseline-v1")
```

**That's it!** No changes needed to routes, schemas, or validation logic.

### Scenario 2: Add OCR for Evidence Extraction

**Step 1:** Install tesseract and pytesseract:
```powershell
pip install pytesseract
# Install Tesseract OCR binary separately
```

**Step 2:** Add OCR service to `app/services/`:

```python
# app/services/ocr.py
import pytesseract
from PIL import Image

class OCRExtractor:
    def extract_text(self, image: Image.Image) -> str:
        """Extract text from image using Tesseract OCR."""
        return pytesseract.image_to_string(image)
    
    def extract_features(self, image: Image.Image) -> dict:
        """Extract structured features from text."""
        text = self.extract_text(image)
        
        # Look for patterns (examples)
        import re
        registration_numbers = re.findall(r'\b\d{4,8}\b', text)
        
        return {
            "text": text,
            "has_registration_number": len(registration_numbers) > 0,
            "registration_numbers": registration_numbers
        }
```

**Step 3:** Use in classifier:

```python
class TrainedClassifier(DocumentClassifier):
    def __init__(self, model_path: str):
        # ... existing init ...
        self.ocr = OCRExtractor()
    
    def classify(self, image: Image.Image) -> ClassificationOutput:
        # ... existing vision model inference ...
        
        # Add OCR features
        try:
            ocr_features = self.ocr.extract_features(image)
            evidence.append(
                "Contains registration number pattern"
                if ocr_features["has_registration_number"]
                else "No clear registration number found"
            )
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
        
        # ... rest of classification ...
```

### Scenario 3: Add a New Document Type

**Step 1:** Add to enum in `app/schemas/__init__.py`:

```python
class DocumentType(str, Enum):
    MEDICAL_REGISTRATION_CERTIFICATE = "medical_registration_certificate"
    MEDICAL_COUNCIL_REGISTRATION = "medical_council_registration"
    PROVISIONAL_REGISTRATION = "provisional_registration"
    SPECIALTY_CERTIFICATE = "specialty_certificate"  # NEW
    UNKNOWN = "unknown"
```

**Step 2:** Retrain your model with examples of the new type.

**Step 3:** Update the label mapping in your classifier to include the new type.

**Step 4:** Add test cases in `tests/test_api.py`.

---

## Confidence Scores: What They Mean

### In the Baseline Classifier

```python
document_type_confidence=0.0
country_confidence=0.0
```

**Meaning:** "I have no confidence in any classification." This is honest - the baseline can't classify.

### In a Trained Classifier

Confidence comes from your model's output. For a neural network:

```python
# Softmax output for document types
doc_type_probs = [0.02, 0.85, 0.10, 0.03]  # Sums to 1.0
# Index 1 (medical_registration_certificate) has highest probability

document_type_confidence = 0.85  # 85% confident
```

**What 0.85 means:**
- The model assigns 85% probability to this class
- It's relatively confident, but not certain
- There's 15% probability it could be something else

**What confidence does NOT mean:**
- ❌ "85% of the time this prediction is correct" (that's accuracy, not confidence)
- ❌ "This document is 85% authentic" (we don't verify authenticity)
- ❌ "You should trust this 85% of the time" (depends on your risk tolerance)

### When Confidence is Misleading

1. **Out-of-distribution inputs:** Model trained on Indian documents, given a Chinese document → might return high confidence on a wrong label

2. **Uncalibrated models:** A neural network's softmax outputs are not true probabilities unless you calibrate them

3. **Dataset bias:** If 90% of training data is one class, model might be overconfident on that class

**Best practice:** Set a threshold (e.g., 0.7) and return `needs_review` for anything below it. Don't trust low-confidence predictions.

---

## Common Modification Scenarios

### Change Upload Size Limit

**Option 1:** Environment variable (no code change)
```
# .env
MAX_FILE_SIZE_MB=20
```

**Option 2:** Code (for dynamic limits)
```python
# app/core/config.py
max_file_size_mb: int = Field(default=20, ...)  # Change default
```

### Add a New Response Field

**Step 1:** Add to schema
```python
# app/schemas/__init__.py
class VerificationResponse(BaseModel):
    # ... existing fields ...
    processing_time_ms: Optional[float] = Field(None, description="Processing time")
```

**Step 2:** Populate in route
```python
# app/main.py
import time

async def verify_document(file: UploadFile = File(...)):
    start = time.time()
    # ... existing code ...
    
    response = VerificationResponse(
        # ... existing fields ...
        processing_time_ms=(time.time() - start) * 1000
    )
```

### Add Authentication

**Step 1:** Install dependency
```powershell
pip install python-jose[cryptography] passlib[bcrypt]
```

**Step 2:** Add security utilities
```python
# app/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token (implement your logic)
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
```

**Step 3:** Protect routes
```python
# app/main.py
from app.core.security import verify_token

@app.post("/api/v1/verify-document", dependencies=[Depends(verify_token)])
async def verify_document(file: UploadFile = File(...)):
    # Now requires valid token
```

### Log to File Instead of Console

```python
# app/main.py
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/api.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logging.getLogger().addHandler(handler)
```

---

## Comprehension Questions

Try answering these without looking back. Answers are in the next section.

### Beginner Level

1. What are the three main layers of the application architecture?

2. Why do we reload the image twice in `ImageValidator.load_and_validate()`?

3. What does `status: needs_review` mean in the response?

4. Where are configuration values like `MAX_FILE_SIZE_MB` loaded from?

5. What happens if someone uploads a 50MB image when the limit is 10MB?

### Intermediate Level

6. Explain the path of an uploaded image from bytes to classification. List at least 6 steps.

7. Why is `ImageValidator` separate from `ImagePreprocessor`?

8. What is the purpose of the `DocumentClassifier` abstract base class?

9. How does the `@lru_cache` decorator on `get_settings()` improve performance?

10. Why do we convert all images to RGB mode before preprocessing?

### Advanced Level

11. How would you add a new endpoint that returns classification statistics (e.g., total requests processed, average confidence scores)? What pattern would you use to track this data?

12. The baseline classifier returns confidence 0.0. A trained model returns confidence 0.85 for a document type. How would you determine if 0.85 is actually reliable?

13. Explain how to implement gradual rollout of a new classifier version (e.g., route 10% of traffic to new model, 90% to old).

14. What security vulnerabilities could arise if we trusted the client-supplied `content_type` instead of validating the actual image format?

15. Design an extension that caches classification results for images that have been uploaded before (same hash). What are the tradeoffs?

---

## Answers to Comprehension Questions

### Beginner Level

**1. Three main layers:**
- HTTP/Routes layer (`app/main.py`)
- Services layer (`app/services/`)
- Configuration layer (`app/core/config.py`)
Schemas (`app/schemas/`) are the contracts between layers.

**2. Why reload the image twice:**
After `image.verify()`, the PIL Image object is in an unusable state (Pillow limitation). We need to reload from bytes to actually use the image. First load verifies integrity, second load is for processing.

**3. `status: needs_review` means:**
The classifier is uncertain or cannot make a confident classification. Manual review is recommended. This is honest behavior when confidence is low or no model is available.

**4. Configuration loaded from:**
Environment variables or `.env` file. The `Settings` class in `app/core/config.py` uses `pydantic_settings` to automatically load them.

**5. 50MB upload when limit is 10MB:**
`ImageValidator.validate_file_size()` raises `ImageValidationError`. The exception handler in `main.py` catches it and returns HTTP 400 with an error message.

### Intermediate Level

**6. Image path from bytes to classification:**
1. Client uploads file as multipart form data
2. FastAPI parses it into `UploadFile` object
3. Read bytes with `await file.read()`
4. `ImageValidator.load_and_validate()` checks size, format, dimensions
5. `ImagePreprocessor.extract_metadata()` captures original properties
6. `ImagePreprocessor.preprocess()` resizes to 512x512 RGB
7. `Classifier.classify()` analyzes the image
8. Results wrapped in `VerificationResponse` and returned as JSON

**7. Why separate validator from preprocessor:**
Different concerns. Validator is about **security** (rejecting bad input). Preprocessor is about **normalization** (transforming good input for the model). Validation happens once; preprocessing might change based on the model.

**8. Purpose of `DocumentClassifier` abstract class:**
Defines the interface all classifiers must implement. This allows swapping baseline for trained model without changing route code. It's the Strategy pattern - multiple implementations of one interface.

**9. `@lru_cache` on `get_settings()`:**
Without it, every call to `get_settings()` would read environment variables from disk/memory. With it, settings are loaded once and cached, improving performance. Since settings don't change during runtime, caching is safe.

**10. Why convert to RGB:**
Ensures consistent input to the classifier. Uploads might be JPEG (RGB), PNG (RGBA with alpha channel), or grayscale (L mode). Converting everything to RGB means the classifier doesn't need to handle multiple color modes.

### Advanced Level

**11. Statistics endpoint implementation:**

```python
# app/services/statistics.py
from dataclasses import dataclass, field
from typing import List
import threading

@dataclass
class Statistics:
    total_requests: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def record_classification(self, confidence: float):
        with self.lock:
            self.total_requests += 1
            self.confidence_scores.append(confidence)
    
    def get_stats(self) -> dict:
        with self.lock:
            return {
                "total_requests": self.total_requests,
                "average_confidence": sum(self.confidence_scores) / len(self.confidence_scores)
                    if self.confidence_scores else 0.0
            }

# In main.py lifespan, initialize global
stats = Statistics()

# In verify_document, after classification:
stats.record_classification(result.document_type_confidence)

# New endpoint:
@app.get("/api/v1/statistics")
def get_statistics():
    return stats.get_stats()
```

**Pattern:** Singleton pattern for global state with thread-safe updates.

**12. Determining if 0.85 confidence is reliable:**

You can't know from the confidence alone. You need:
- **Calibration curve:** Plot predicted confidence vs actual accuracy on a held-out validation set
- **Test set evaluation:** If the model is 85% accurate on test data, then 0.85 confidence is meaningful
- **Per-class metrics:** Maybe 0.85 is reliable for common classes but not rare ones
- **Confidence intervals:** Statistical uncertainty around the prediction

**Best practice:** Evaluate on a proper test set, plot calibration curves, set thresholds based on your precision/recall requirements.

**13. Gradual rollout implementation:**

```python
import random

class ClassifierFactory:
    @staticmethod
    def create_classifier(model_path: Optional[str] = None, rollout_percent: int = 100) -> DocumentClassifier:
        # Randomly route X% to new model
        use_new_model = random.randint(1, 100) <= rollout_percent
        
        if use_new_model and model_path and Path(model_path).exists():
            try:
                return TrainedClassifierV2(model_path)
            except Exception:
                pass
        
        # Default to stable model
        return TrainedClassifierV1("models/stable_v1.pkl")

# In config.py, add:
model_rollout_percent: int = Field(default=10, ge=0, le=100)

# In main.py lifespan:
classifier = ClassifierFactory.create_classifier(
    model_path=settings.model_path,
    rollout_percent=settings.model_rollout_percent
)
```

Set `MODEL_ROLLOUT_PERCENT=10` to route 10% to new model.

**14. Security vulnerabilities from trusting content_type:**

- **MIME type spoofing:** Attacker uploads malicious executable with `Content-Type: image/jpeg`
- **Bypass filters:** If downstream code trusts the type, it might execute the file
- **Path traversal:** If filename is used in file paths, `../../etc/passwd` could access sensitive files
- **Resource exhaustion:** Upload a massive XML file claiming to be PNG, exhaust parser memory

**Our defense:** Always validate actual file format by reading bytes with PIL. Never trust client input.

**15. Caching classification results:**

```python
import hashlib
from functools import lru_cache

def compute_hash(file_data: bytes) -> str:
    return hashlib.sha256(file_data).hexdigest()

# In-memory cache (simple but not persistent)
classification_cache = {}

# In verify_document, before classification:
file_hash = compute_hash(file_data)
if file_hash in classification_cache:
    return classification_cache[file_hash]

# After classification:
classification_cache[file_hash] = response
```

**Tradeoffs:**
- ✅ **Pro:** Faster responses for duplicate uploads
- ✅ **Pro:** Reduced compute cost
- ❌ **Con:** Memory usage grows unbounded
- ❌ **Con:** Cache invalidation when model is updated
- ❌ **Con:** Privacy concern - storing hashes of medical documents
- ❌ **Con:** Not persistent across restarts

**Better approach:** Use Redis with TTL and implement cache invalidation on model updates.

---

## Learning Roadmap

When you want to modify this system, tackle these in order:

### Week 1: Understand the Foundation
1. Read through `app/main.py` and trace one request from route to response
2. Experiment with `.env` configuration - change limits and see effects
3. Run tests and understand what each test validates
4. Add a simple new route (e.g., `/api/v1/version` that returns app version)

### Week 2: Services Layer
1. Read `app/services/image_processing.py` - understand validation logic
2. Add a new validation rule (e.g., reject images with extreme aspect ratios)
3. Read `app/services/classifier.py` - understand the interface pattern
4. Modify baseline classifier to detect color photos vs documents

### Week 3: Real Data
1. Collect 10-20 sample medical documents (or create synthetic ones)
2. Write a dataset audit script that reports class counts, duplicates, quality issues
3. Manually label them by document type
4. Organize in `data/train/` and `data/test/` directories

### Week 4: Training (if you have ML experience)
1. Write a training script that loads your dataset
2. Train a simple CNN or use transfer learning (ResNet, EfficientNet)
3. Evaluate on test set - report accuracy, confusion matrix
4. Implement `TrainedClassifier` class

### Week 5: Production Readiness
1. Add authentication to protect the endpoint
2. Set up proper logging to files
3. Add request rate limiting
4. Write deployment documentation

---

**You now have a complete, production-grade API foundation. When training data becomes available, you have a clear path to plug in a real classifier. The architecture is designed for exactly this evolution.**

