from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli import aws_marketplace  # noqa: E402


class AwsMarketplaceAdapterTests(unittest.TestCase):
    def test_current_content_normalizes_read_shape(self) -> None:
        entity = {
            "EntityType": "AmiProduct@1.0",
            "DetailsDocument": {
                "Description": {
                    "ProductTitle": "Title",
                    "ShortDescription": "Short",
                    "LongDescription": "Long",
                    "Highlights": ["One"],
                    "SearchKeywords": ["keyword"],
                    "Categories": ["CRM"],
                },
                "PromotionalResources": {
                    "LogoUrl": "https://example.com/logo.png",
                    "Videos": [{"Url": "https://example.com/video.mp4"}],
                    "AdditionalResources": [
                        {"Type": "Link", "Text": "Guide", "Url": "https://example.com/guide"}
                    ],
                },
                "SupportInformation": {"Description": "Support details"},
            },
        }

        current = aws_marketplace.current_content(entity)

        self.assertEqual(current["VideoUrls"], ["https://example.com/video.mp4"])
        self.assertEqual(current["SupportDescription"], "Support details")
        self.assertEqual(current["AdditionalResources"],
                         [{"Text": "Guide", "Url": "https://example.com/guide"}])
        self.assertNotIn("Type", current["AdditionalResources"][0])

    def test_read_and_update_documents_use_distinct_aws_shapes(self) -> None:
        content = {
            "ProductTitle": "Title",
            "ShortDescription": "Short",
            "LongDescription": "Long",
            "Highlights": ["One"],
            "SearchKeywords": ["keyword"],
            "Categories": ["CRM"],
            "LogoUrl": "https://example.com/logo.png",
            "VideoUrls": ["https://example.com/video.mp4"],
            "AdditionalResources": [{"Text": "Guide", "Url": "https://example.com/guide"}],
            "SupportDescription": "Support details",
        }

        desired = aws_marketplace.to_read_document(content)
        update = aws_marketplace.to_update_document(content)

        self.assertEqual(desired["PromotionalResources"]["Videos"], ["https://example.com/video.mp4"])
        self.assertEqual(desired["PromotionalResources"]["AdditionalResources"],
                         [{"Type": "Link", "Text": "Guide", "Url": "https://example.com/guide"}])
        self.assertEqual(desired["SupportInformation"]["Description"], "Support details")
        self.assertNotIn("SupportDescription", desired["Description"])
        self.assertEqual(update["VideoUrls"], ["https://example.com/video.mp4"])
        self.assertEqual(update["SupportDescription"], "Support details")
        self.assertEqual(update["AdditionalResources"], [{"Text": "Guide", "Url": "https://example.com/guide"}])
        self.assertNotIn("Type", update["AdditionalResources"][0])

    def test_field_contract_covers_read_and_write_paths(self) -> None:
        self.assertEqual(aws_marketplace.CONTENT_FIELDS, set(aws_marketplace.FIELD_SPECS))
        self.assertEqual(
            aws_marketplace.FIELD_LIMITS["ProductTitle"],
            aws_marketplace.FIELD_SPECS["ProductTitle"]["max"],
        )
        for field, spec in aws_marketplace.FIELD_SPECS.items():
            self.assertIn("read", spec, field)
            self.assertIn("write", spec, field)
            self.assertIn("type", spec, field)

    def test_update_request_uses_flat_update_information_shape(self) -> None:
        request = aws_marketplace.build_update_request(
            {"entityType": "AmiProduct@1.0"},
            "prod-example@4",
            {"AdditionalResources": [{"Text": "Guide", "Url": "https://example.com/guide"}]},
        )

        self.assertEqual(request["Catalog"], "AWSMarketplace")
        change = request["ChangeSet"][0]
        self.assertEqual(change["ChangeType"], "UpdateInformation")
        self.assertEqual(change["Entity"]["Identifier"], "prod-example@4")
        self.assertEqual(change["DetailsDocument"]["AdditionalResources"],
                         [{"Text": "Guide", "Url": "https://example.com/guide"}])

    def test_empty_update_request_is_none(self) -> None:
        self.assertIsNone(aws_marketplace.build_update_request(
            {"entityType": "AmiProduct@1.0"}, "prod-example@4", {}))


if __name__ == "__main__":
    unittest.main()
