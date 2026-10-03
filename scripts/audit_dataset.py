"""Dataset audit script - run before training any model."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set

from PIL import Image


class DatasetAuditor:
    """Audit a dataset for training readiness."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict = {}

    def audit(self) -> Dict:
        """Run complete audit and return report."""
        print("=" * 60)
        print("Dataset Audit Report")
        print("=" * 60)
        print(f"Directory: {self.data_dir}\n")

        if not self.data_dir.exists():
            print(f"❌ Error: Directory does not exist: {self.data_dir}")
            return {"error": "Directory not found"}

        # Run checks
        self._check_structure()
        self._scan_images()
        self._check_duplicates()
        self._check_distribution()
        self._check_quality()

        # Print summary
        self._print_summary()

        return self.stats

    def _check_structure(self):
        """Check directory structure."""
        print("1. Checking directory structure...")

        expected_structure = ["train", "test"]
        found_dirs = [d.name for d in self.data_dir.iterdir() if d.is_dir()]

        self.stats["structure"] = {
            "root_dir": str(self.data_dir),
            "subdirs": found_dirs,
        }

        if not any(d in found_dirs for d in expected_structure):
            self.warnings.append(
                "No train/test split found. Consider organizing as data/train/ and data/test/"
            )
        else:
            print(f"   ✓ Found split directories: {found_dirs}")

    def _scan_images(self):
        """Scan all images and collect metadata."""
        print("\n2. Scanning images...")

        image_extensions = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}
        images_by_class = defaultdict(list)
        all_images = []

        for image_path in self.data_dir.rglob("*"):
            if image_path.suffix.lower() in image_extensions:
                # Determine class from parent directory name
                class_name = image_path.parent.name
                images_by_class[class_name].append(image_path)
                all_images.append(image_path)

        self.stats["total_images"] = len(all_images)
        self.stats["classes"] = {
            cls: len(images) for cls, images in images_by_class.items()
        }
        self.all_images = all_images
        self.images_by_class = images_by_class

        print(f"   Total images: {len(all_images)}")
        print(f"   Classes found: {len(images_by_class)}")
        for cls, images in sorted(images_by_class.items()):
            print(f"     - {cls}: {len(images)} images")

        if len(all_images) == 0:
            self.issues.append("No images found in dataset directory")
        elif len(all_images) < 50:
            self.warnings.append(
                f"Very small dataset ({len(all_images)} images). "
                "Deep learning models typically need hundreds or thousands of examples."
            )

    def _check_duplicates(self):
        """Check for duplicate images by hash."""
        print("\n3. Checking for duplicates...")

        hashes: Dict[str, List[Path]] = defaultdict(list)

        for img_path in self.all_images:
            try:
                with open(img_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    hashes[file_hash].append(img_path)
            except Exception as e:
                self.warnings.append(f"Could not read {img_path}: {e}")

        duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}

        self.stats["duplicates"] = len(duplicates)

        if duplicates:
            print(f"   ⚠️  Found {len(duplicates)} duplicate image groups:")
            for file_hash, paths in list(duplicates.items())[:5]:  # Show first 5
                print(f"      Hash {file_hash[:16]}...")
                for path in paths:
                    print(f"        - {path}")
            if len(duplicates) > 5:
                print(f"      ... and {len(duplicates) - 5} more")

            self.warnings.append(
                f"Found {len(duplicates)} duplicate images. "
                "Consider removing duplicates to avoid data leakage."
            )
        else:
            print("   ✓ No duplicate images found")

    def _check_distribution(self):
        """Check class distribution and balance."""
        print("\n4. Checking class distribution...")

        class_counts = self.stats["classes"]

        if not class_counts:
            return

        min_count = min(class_counts.values())
        max_count = max(class_counts.values())
        imbalance_ratio = max_count / min_count if min_count > 0 else float("inf")

        self.stats["class_imbalance_ratio"] = imbalance_ratio

        print(f"   Min class size: {min_count}")
        print(f"   Max class size: {max_count}")
        print(f"   Imbalance ratio: {imbalance_ratio:.2f}x")

        if imbalance_ratio > 3:
            self.warnings.append(
                f"High class imbalance ({imbalance_ratio:.1f}x). "
                "Consider oversampling minority classes or using class weights."
            )
        else:
            print("   ✓ Classes are relatively balanced")

        # Check train/test distribution
        train_dir = self.data_dir / "train"
        test_dir = self.data_dir / "test"

        if train_dir.exists() and test_dir.exists():
            train_images = list(train_dir.rglob("*.jpg")) + list(
                train_dir.rglob("*.png")
            )
            test_images = list(test_dir.rglob("*.jpg")) + list(test_dir.rglob("*.png"))

            total = len(train_images) + len(test_images)
            if total > 0:
                test_ratio = len(test_images) / total
                print(f"\n   Train/test split: {len(train_images)}/{len(test_images)}")
                print(f"   Test set ratio: {test_ratio:.1%}")

                if test_ratio < 0.1:
                    self.warnings.append(
                        f"Test set is only {test_ratio:.1%} of data. "
                        "Consider 10-20% for test set."
                    )
                elif test_ratio > 0.3:
                    self.warnings.append(
                        f"Test set is {test_ratio:.1%} of data. "
                        "This leaves less data for training."
                    )

    def _check_quality(self):
        """Check image quality issues."""
        print("\n5. Checking image quality...")

        issues = {
            "corrupted": [],
            "too_small": [],
            "unusual_format": [],
            "unusual_aspect": [],
        }

        for img_path in self.all_images:
            try:
                with Image.open(img_path) as img:
                    width, height = img.size

                    # Check size
                    if width < 100 or height < 100:
                        issues["too_small"].append((img_path, width, height))

                    # Check aspect ratio
                    aspect = width / height if height > 0 else 0
                    if aspect < 0.3 or aspect > 3.0:
                        issues["unusual_aspect"].append((img_path, aspect))

                    # Check format
                    if img.format not in ["JPEG", "PNG"]:
                        issues["unusual_format"].append((img_path, img.format))

            except Exception as e:
                issues["corrupted"].append((img_path, str(e)))

        # Report issues
        total_issues = sum(len(v) for v in issues.values())

        if issues["corrupted"]:
            print(f"   ❌ {len(issues['corrupted'])} corrupted/unreadable images:")
            for img_path, error in issues["corrupted"][:3]:
                print(f"      - {img_path}: {error}")
            if len(issues["corrupted"]) > 3:
                print(f"      ... and {len(issues['corrupted']) - 3} more")

        if issues["too_small"]:
            print(f"   ⚠️  {len(issues['too_small'])} images smaller than 100x100:")
            for img_path, w, h in issues["too_small"][:3]:
                print(f"      - {img_path}: {w}x{h}")

        if issues["unusual_aspect"]:
            print(
                f"   ⚠️  {len(issues['unusual_aspect'])} images with unusual aspect ratio:"
            )
            for img_path, aspect in issues["unusual_aspect"][:3]:
                print(f"      - {img_path}: {aspect:.2f}")

        if issues["unusual_format"]:
            print(f"   ⚠️  {len(issues['unusual_format'])} images in unusual format:")
            for img_path, fmt in issues["unusual_format"][:3]:
                print(f"      - {img_path}: {fmt}")

        if total_issues == 0:
            print("   ✓ No quality issues found")

        self.stats["quality_issues"] = {k: len(v) for k, v in issues.items()}

    def _print_summary(self):
        """Print final summary."""
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)

        if self.issues:
            print("\n❌ CRITICAL ISSUES:")
            for issue in self.issues:
                print(f"   - {issue}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")

        if not self.issues and not self.warnings:
            print("\n✓ No critical issues found!")
            print("  Dataset appears ready for training.")

        print("\n" + "=" * 60)
        print("Recommendations:")
        print("=" * 60)
        print("1. Review any warnings above before training")
        print("2. Remove duplicate images across train/test splits")
        print("3. Ensure train and test sets contain different patients/documents")
        print("4. Consider data augmentation for small datasets")
        print("5. Use stratified splitting to maintain class distribution")
        print("=" * 60 + "\n")


def main():
    """Run dataset audit."""
    import sys

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = "data"

    auditor = DatasetAuditor(data_dir)
    report = auditor.audit()

    # Save report
    report_path = Path(data_dir) / "audit_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
