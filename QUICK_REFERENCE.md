# Quick Reference - Medical Document Verification API

## Essential Commands

### Setup
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create config file (optional)
Copy-Item .env.example .env
```

### Running

```powershell
# Start development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Start production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing

```powershell
# Run all tests
pytest

# Run specific test class
pytest tests/test_api.py::TestDocumentVerification -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```powershell
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type check
mypy app/
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Basic health check |
| `/health` | GET | Service health status |
| `/api/v1/status` | GET | Classifier readiness & version |
| `/api/v1/verify-document` | POST | Verify document image |
| `/docs` | GET | Interactive API documentation |

---

## Example API Call

```bash
curl -X POST http://127.0.0.1:8000/api/v1/verify-document \
  -F "file=@document.jpg" \
  -H "Accept: application/json"
```

Or with Python:
```python
import requests

with open("document.jpg", "rb") as f:
    files = {"file": ("document.jpg", f, "image/jpeg")}
    response = requests.post(
        "http://127.0.0.1:8000/api/v1/verify-document",
        files=files
    )
    print(response.json())
```

---

## Project Structure Quick Map

```
app/
├── main.py                  → Routes, middleware, application lifecycle
├── core/
│   └── config.py           → Environment-based configuration
├── schemas/
│   └── __init__.py         → Request/response models (Pydantic)
└── services/
    ├── classifier.py       → Classification interface & baseline
    └── image_processing.py → Validation & preprocessing

tests/
└── test_api.py             → Comprehensive test suite

.env.example                → Configuration template
requirements.txt            → Python dependencies
README.md                   → Full documentation
LEARNING_GUIDE.md          → Detailed walkthrough & tutorials
```

---

## Key Files to Know

| File | What to Change |
|------|----------------|
| `app/main.py` | Add routes, modify API behavior |
| `app/services/classifier.py` | Add trained model implementation |
| `app/schemas/__init__.py` | Add response fields, new enums |
| `app/core/config.py` | Add configuration options |
| `.env` | Change limits, ports, settings (don't commit!) |

---

## Configuration Quick Reference

Set in `.env` or environment variables:

```bash
# Upload limits
MAX_FILE_SIZE_MB=10
MAX_IMAGE_WIDTH=4096
MAX_IMAGE_HEIGHT=4096
MAX_IMAGE_PIXELS=16777216

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
RELOAD=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Model
MODEL_PATH=models/classifier.pkl
MODEL_VERSION=baseline-v1
CONFIDENCE_THRESHOLD=0.7

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## Common Tasks

### Add a new document type
1. Edit `app/schemas/__init__.py` → Add to `DocumentType` enum
2. Retrain classifier with new type
3. Update classifier label mappings
4. Add test cases

### Add a new country
1. Edit `app/schemas/__init__.py` → Add to `Country` enum
2. Retrain classifier with new examples
3. Update documentation

### Change upload limits
- **Quick:** Edit `.env` → Set `MAX_FILE_SIZE_MB=20`
- **Code:** Edit `app/core/config.py` → Change default values

### Add authentication
1. `pip install python-jose[cryptography] passlib[bcrypt]`
2. Create `app/core/security.py` with token verification
3. Add `dependencies=[Depends(verify_token)]` to protected routes

### Replace baseline with trained model
1. Implement `TrainedClassifier(DocumentClassifier)` in `classifier.py`
2. Update `ClassifierFactory.create_classifier()` to load it
3. Save model to `models/classifier.pkl`
4. Set `MODEL_PATH=models/classifier.pkl` in `.env`

---

## Response Status Values

| Status | Meaning | When |
|--------|---------|------|
| `classified` | Confident prediction | Trained model with high confidence |
| `needs_review` | Uncertain | Low confidence or baseline classifier |
| `unavailable` | Service error | Classifier not loaded |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests fail with import errors | Activate venv: `.\.venv\Scripts\Activate.ps1` |
| API returns 503 | Check startup logs for classifier initialization errors |
| Large images rejected | Increase `MAX_IMAGE_WIDTH/HEIGHT` in `.env` |
| CORS errors | Add origin to `CORS_ORIGINS` in `.env` |
| Module not found | `pip install -r requirements.txt` |

---

## Important Security Notes

✅ **What we do:**
- Validate actual file format (not just MIME type)
- Enforce size and dimension limits
- Never persist uploads by default
- Sanitize filenames
- Don't log sensitive content

❌ **What we DON'T do (by design):**
- Verify registration against official registries
- Confirm document authenticity
- Provide legal verification
- Store document submissions

---

## Next Steps

1. **Read:** `LEARNING_GUIDE.md` for detailed architecture walkthrough
2. **Explore:** API at http://127.0.0.1:8000/docs (interactive)
3. **Experiment:** Run `example_usage.py` to see it in action
4. **Extend:** Follow learning roadmap in `LEARNING_GUIDE.md`

---

## Useful Links

- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Pydantic Docs:** https://docs.pydantic.dev
- **Pillow Docs:** https://pillow.readthedocs.io
- **Pytest Docs:** https://docs.pytest.org

---

## Quick Wins

Want to see changes quickly? Try these:

1. **Change response message:** Edit `app/main.py` line 144 → Change health check message
2. **Add logging:** Add `logger.info(f"Processing {file.filename}")` in `verify_document()`
3. **Modify evidence:** Edit `BaselineClassifier.classify()` → Change evidence strings
4. **Add validation:** Edit `ImageValidator` → Add new check (e.g., min aspect ratio)

---

**Remember:** This is a foundation designed for extension. The baseline classifier is honest about its limitations. When you have training data, you have a clear path to add a real classifier without rewriting the API.
