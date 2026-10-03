"""Document classifier interface and baseline implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from app.schemas import Country, DocumentType, VerificationStatus


@dataclass
class ClassificationOutput:
    """Output from document classifier."""

    status: VerificationStatus
    genuine_looking: Optional[bool]
    document_type: str
    document_type_confidence: float
    country: str
    country_confidence: float
    evidence: list[str]


class DocumentClassifier(ABC):
    """Abstract base class for document classifiers."""

    @abstractmethod
    def classify(self, image: Image.Image) -> ClassificationOutput:
        """
        Classify a medical registration document image.

        Args:
            image: Preprocessed PIL Image

        Returns:
            ClassificationOutput with predictions and confidence scores
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the classifier is loaded and ready.

        Returns:
            True if classifier can process requests
        """
        pass

    @abstractmethod
    def get_version(self) -> Optional[str]:
        """
        Get the classifier version identifier.

        Returns:
            Version string or None if unavailable
        """
        pass


class BaselineClassifier(DocumentClassifier):
    """
    Baseline rule-based classifier.

    This is a placeholder implementation that honestly reports when
    classification cannot be performed with confidence.

    USE CASE:
    - No training data available
    - No trained model weights
    - Demonstrates API contract and integration points

    BEHAVIOR:
    - Always returns status='needs_review'
    - Performs basic image feature extraction (aspect ratio, size)
    - Does NOT claim to verify authenticity
    - Clearly states limitations

    When real training data becomes available, replace this with a
    trained classifier that implements the same interface.
    """

    def __init__(self, version: str = "baseline-v1"):
        """
        Initialize baseline classifier.

        Args:
            version: Version identifier for this baseline
        """
        self.version = version
        self._available = True

    def classify(self, image: Image.Image) -> ClassificationOutput:
        """
        Perform baseline classification (rule-based heuristics).

        Current implementation returns 'needs_review' with basic
        image feature analysis. This is honest behavior when no
        trained model is available.

        Args:
            image: Preprocessed PIL Image in RGB mode

        Returns:
            ClassificationOutput with needs_review status
        """
        width, height = image.size
        aspect_ratio = width / height if height > 0 else 1.0

        # Basic heuristics for document-like images
        # These are NOT classification - just sanity checks
        looks_document_shaped = 0.5 < aspect_ratio < 2.0
        reasonable_size = width >= 200 and height >= 200

        # Extract basic features for evidence
        evidence = []
        if looks_document_shaped:
            evidence.append(
                f"Image has document-like aspect ratio ({aspect_ratio:.2f})"
            )
        else:
            evidence.append(
                f"Unusual aspect ratio ({aspect_ratio:.2f}) for a document"
            )

        if reasonable_size:
            evidence.append(f"Image resolution is adequate ({width}x{height})")
        else:
            evidence.append(f"Low image resolution ({width}x{height})")

        # Honest output: we cannot classify without a trained model
        evidence.append(
            "Baseline classifier active - no trained model available"
        )
        evidence.append(
            "Manual review recommended for actual document verification"
        )

        return ClassificationOutput(
            status=VerificationStatus.NEEDS_REVIEW,
            genuine_looking=None,  # Cannot determine without trained model
            document_type=DocumentType.UNKNOWN.value,
            document_type_confidence=0.0,
            country=Country.UNKNOWN.value,
            country_confidence=0.0,
            evidence=evidence,
        )

    def is_available(self) -> bool:
        """
        Check if baseline classifier is available.

        Returns:
            Always True (baseline is always available)
        """
        return self._available

    def get_version(self) -> Optional[str]:
        """
        Get baseline classifier version.

        Returns:
            Version string
        """
        return self.version


class ClassifierFactory:
    """Factory for creating classifier instances."""

    @staticmethod
    def create_classifier(
        model_path: Optional[str] = None,
        version: Optional[str] = None
    ) -> DocumentClassifier:
        """
        Create a classifier instance.

        Currently returns BaselineClassifier. When a trained model
        becomes available, this factory should:
        1. Check if model_path exists
        2. Load the trained model if available
        3. Fall back to baseline if model loading fails

        Args:
            model_path: Path to trained model file (unused in baseline)
            version: Model version identifier

        Returns:
            DocumentClassifier instance
        """
        # Future: Load trained model from model_path if it exists
        # For now, always return baseline
        return BaselineClassifier(version=version or "baseline-v1")
