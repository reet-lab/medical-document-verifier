"""Example script demonstrating API usage."""

import io
import requests
from PIL import Image


def create_sample_document():
    """Create a sample document image for testing."""
    # Create a simple document-like image
    img = Image.new("RGB", (800, 1000), color="white")

    # Save to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.getvalue()


def main():
    base_url = "http://127.0.0.1:8000"

    # 1. Check service health
    print("1. Checking service health...")
    response = requests.get(f"{base_url}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")

    # 2. Check service status
    print("2. Checking service status...")
    response = requests.get(f"{base_url}/api/v1/status")
    status = response.json()
    print(f"   Classifier loaded: {status['classifier_loaded']}")
    print(f"   Model version: {status['model_version']}")
    print(f"   Supported formats: {status['supported_formats']}\n")

    # 3. Verify a document
    print("3. Verifying a document...")
    document_bytes = create_sample_document()

    files = {"file": ("test_document.jpg", document_bytes, "image/jpeg")}
    response = requests.post(f"{base_url}/api/v1/verify-document", files=files)

    if response.status_code == 200:
        result = response.json()
        print(f"   Request ID: {result['request_id']}")
        print(f"   Status: {result['status']}")
        print(f"   Document type: {result['document_type']['label']} "
              f"(confidence: {result['document_type']['confidence']})")
        print(f"   Country: {result['country']['label']} "
              f"(confidence: {result['country']['confidence']})")
        print(f"   Evidence:")
        for evidence in result['evidence']:
            print(f"     - {evidence}")
        print(f"\n   Image metadata:")
        print(f"     Format: {result['image']['format']}")
        print(f"     Size: {result['image']['width']}x{result['image']['height']}")
        print(f"     Mode: {result['image']['mode']}")
    else:
        print(f"   Error: {response.status_code}")
        print(f"   {response.json()}")


if __name__ == "__main__":
    print("Medical Document Verification API - Example Usage\n")
    print("Make sure the API is running:")
    print("  uvicorn app.main:app --reload\n")
    print("=" * 60 + "\n")

    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API.")
        print("   Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
