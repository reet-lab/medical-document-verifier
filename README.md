# Medical Document Verification API

A FastAPI-based classification service for medical registration documents. The API analyzes uploaded document images and estimates document type, country/jurisdiction, and provides confidence scores.

**Important:** This service performs **document appearance classification only**. It does **not** verify registration against official authorities, confirm authenticity, or provide legal verification.

---

## Current Status

**Dataset:** No training data currently available in this repository.

**Classifier:** Baseline rule-based implementation that honestly returns `needs_review` status. When labeled training data becomes available, the baseline can be replaced with a trained model using the same interface.

**API:** Fully functional with production-grade validation, security controls, and error handling.

---

## Features

- ✅ Secure image upload with format validation (JPEG, PNG)
- ✅ File size and dimension limits
- ✅ Byte-level format verification (prevents MIME spoofing)
- ✅ Production-ready FastAPI application
- ✅ OpenAPI documentation
- ✅ Comprehensive test suite
- ✅ Configuration via environment variables
- ✅ CORS support
- ✅ Request logging with timing
- ⏳ Trained classifier (pending labeled dataset)

---

## Quick Start

### Prerequisites

- Python 3.13 or higher
- Virtual environment (recommended)

### Installation

1. **Clone or navigate to the repository:**
   ```powershell
   cd "C:\Users\LENOVO\Desktop\medical document verifier"
   ```

2. **Activate the virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Create configuration (optional):**
   ```powershell
   Copy-Item .env.example .env
   # Edit .env to customize settings
   ```

### Running the API

Start the development server:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:
- **API:** http://127.0.0.1:8000
- **Interactive docs:** http://127.0.0.1:8000/docs
- **OpenAPI spec:** http://127.0.0.1:8000/openapi.json

### Running Tests

Run the full test suite:

```powershell
pytest
```

Run with coverage:

```powershell
pytest --cov=app --cov-report=html
```

Run specific test classes:

```powershell
pytest tests/test_api.py::TestHealthEndpoints
pytest tests/test_api.py::TestDocumentVerification
```

---

## API Usage

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

Response:
```json
{
  "status": "healthy",
  "message": "Service is operational"
}
```

### Service Status

```bash
curl http://127.0.0.1:8000/api/v1/status
```

Response:
```json
{
  "service": "Medical Document Verification API",
  "version": "1.0.0",
  "classifier_loaded": true,
  "model_version": "baseline-v1",
  "supported_formats": ["JPEG", "PNG"]
}
```

### Verify Document

```bash
curl -X POST http://127.0.0.1:8000/api/v1/verify-document \
  -F "file=@path/to/document.jpg"
```

Response:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "needs_review",
  "genuine_looking": null,
  "document_type": {
    "label": "unknown",
    "confidence": 0.0
  },
  "country": {
    "label": "unknown",
    "confidence": 0.0
  },
  "evidence": [
    "Image has document-like aspect ratio (0.75)",
    "Image resolution is adequate (800x1000)",
    "Baseline classifier active - no trained model available",
    "Manual review recommended for actual document verification"
  ],
  "limitations": [
    "Classification does not verify registration against an official authority.",
    "This service estimates document appearance only, not authenticity or validity."
  ],
  "image": {
    "format": "JPEG",
    "width": 800,
    "height": 1000,
    "mode": "RGB",
    "size_bytes": 245678
  }
}
```

### Response Status Values

| Status | Meaning |
|--------|---------|
| `classified` | Confident prediction with evidence (requires trained model) |
| `needs_review` | Uncertain or out-of-distribution; manual review recommended |
| `unavailable` | Classifier not loaded or service error |

---

## Configuration

Settings are loaded from environment variables or `.env` file. See `.env.example` for all options.

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE_MB` | 10 | Maximum upload size in megabytes |
| `MAX_IMAGE_WIDTH` | 4096 | Maximum image width in pixels |
| `MAX_IMAGE_HEIGHT` | 4096 | Maximum image height in pixels |
| `MAX_IMAGE_PIXELS` | 16777216 | Maximum total pixels |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CONFIDENCE_THRESHOLD` | 0.7 | Minimum confidence for classification |

---

## Project Structure

```
medical document verifier/
├── app/
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application and routes
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py            # Configuration management
│   ├── schemas/
│   │   └── __init__.py          # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       ├── classifier.py        # Document classifier interface and baseline
│       └── image_processing.py  # Image validation and preprocessing
├── tests/
│   ├── conftest.py              # Pytest configuration
│   └── test_api.py              # Comprehensive test suite
├── models/                      # Model artifacts (not committed)
├── .env.example                 # Example environment configuration
├── .gitignore                   # Git ignore patterns
├── requirements.txt             # Python dependencies
├── setup.cfg                    # Tool configuration
└── README.md                    # This file
```

---

## Adding Training Data and a Trained Model

### Current State: No Dataset

This repository currently has **no training data**. The baseline classifier returns `needs_review` for all uploads, which is honest behavior when no model is available.

### When You Have Labeled Data

To train and deploy a real classifier:

1. **Organize your dataset:**
   ```
   data/
   ├── train/
   │   ├── medical_registration_certificate/
   │   ├── medical_council_registration/
   │   └── provisional_registration/
   ├── test/
   │   └── (same structure)
   └── labels.csv  # Optional metadata
   ```

2. **Create a training script** (example: `scripts/train.py`):
   - Load and audit the dataset
   - Check for duplicates, train/test leakage, class imbalance
   - Split data appropriately (avoid related documents across splits)
   - Train a classifier (e.g., CNN, vision transformer, or OCR + traditional ML)
   - Evaluate on held-out test set
   - Save model weights to `models/`

3. **Implement a trained classifier** in `app/services/classifier.py`:
   ```python
   class TrainedClassifier(DocumentClassifier):
       def __init__(self, model_path: str):
           # Load your trained model
           self.model = load_model(model_path)
       
       def classify(self, image: Image.Image) -> ClassificationOutput:
           # Run inference
           predictions = self.model.predict(image)
           # Return structured output
           return ClassificationOutput(...)
   ```

4. **Update the factory** in `ClassifierFactory.create_classifier()`:
   ```python
   if model_path and Path(model_path).exists():
       return TrainedClassifier(model_path)
   else:
       return BaselineClassifier()
   ```

5. **Run evaluation and update documentation** with actual metrics.

### Dataset Audit Requirements

Before training, always audit your dataset:

```python
# Example audit checks
- Total images per class
- Train/test split sizes
- Duplicate images (hash-based)
- Image quality issues (corrupted, too small, etc.)
- Label distribution and imbalance
- Potential data leakage (same patient, same scan session across splits)
```

**Never report fabricated metrics.** Only report evaluation results from a defensible held-out test set.

---

## Security and Privacy

### Upload Security

- File size limited to 10MB by default
- Image dimensions validated (min 100x100, max 4096x4096)
- Format validated at byte level (prevents MIME spoofing)
- Malformed and corrupted images rejected
- User-supplied filenames sanitized and not used for filesystem operations

### Privacy

- Uploaded images are **not persisted** to disk
- Logs do **not** contain image data or OCR text
- User filenames not exposed in responses
- Sensitive content not included in error messages

### Production Deployment Notes

Before deploying to production:

1. Set `DEBUG=false` and `RELOAD=false`
2. Configure appropriate CORS origins (don't use `*`)
3. Use HTTPS (terminate TLS at reverse proxy)
4. Set up proper request rate limiting
5. Monitor and rotate logs
6. Don't commit `.env` or model artifacts with sensitive data
7. Review upload limits for your use case
8. Consider adding authentication/authorization

---

## Limitations

This service:

- ❌ **Does NOT verify** registration against official medical councils or authorities
- ❌ **Does NOT confirm** document authenticity or detect forgery
- ❌ **Does NOT provide** legal verification or compliance certification
- ❌ **Does NOT store** or track document submissions
- ✅ **Only estimates** document appearance and type based on visual features

Classification output should be used as a **preliminary filter** or **triage tool**, not as authoritative verification.

---

## Development

### Code Formatting

Format code with Black:

```powershell
black app/ tests/
```

### Linting

Run Ruff:

```powershell
ruff check app/ tests/
```

### Type Checking

Run mypy (optional, currently configured permissively):

```powershell
mypy app/
```

### Adding New Document Types

1. Add enum values to `DocumentType` in `app/schemas/__init__.py`
2. Update classifier to recognize the new type
3. Add test cases in `tests/test_api.py`
4. Retrain and evaluate with examples of the new type

### Adding New Countries

1. Add enum values to `Country` in `app/schemas/__init__.py`
2. Update classifier training data and model
3. Update documentation with coverage claims

---

## Troubleshooting

### Issue: Tests fail with import errors

**Solution:** Make sure you're in the project root and the virtual environment is activated:
```powershell
cd "C:\Users\LENOVO\Desktop\medical document verifier"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: API returns 503 "classifier unavailable"

**Solution:** Check the startup logs. The baseline classifier should always be available. If you see this, check for exceptions during app initialization.

### Issue: Large images rejected

**Solution:** Adjust `MAX_IMAGE_WIDTH`, `MAX_IMAGE_HEIGHT`, or `MAX_IMAGE_PIXELS` in `.env`. Be cautious with memory usage.

### Issue: CORS errors in browser

**Solution:** Add your frontend origin to `CORS_ORIGINS` in `.env`:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,https://yourapp.com
```

---

## Future Enhancements

When training data becomes available:

- [ ] Train a CNN or vision transformer classifier
- [ ] Add OCR-based text extraction for evidence
- [ ] Multi-label classification (document can be multiple types)
- [ ] Anomaly detection for out-of-distribution images
- [ ] Support for additional document types and jurisdictions
- [ ] Confidence calibration and uncertainty quantification
- [ ] Model versioning and A/B testing
- [ ] Integration with official registry APIs for verification

---

## License

[Add your license here]

---

## Contact

[Add contact information or support channels]
