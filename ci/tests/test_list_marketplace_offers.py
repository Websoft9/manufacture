from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import list_marketplace_offers as offers


class AccessDeniedException(Exception):
    def __init__(self) -> None:
        super().__init__("denied")
        self.response = {"Error": {"Code": "AccessDeniedException"}}


class FakeClient:
    def __init__(self) -> None:
        self.list_requests: list[dict] = []
        self.describe_requests: list[dict] = []
        self.pages = [
            {
                "NextToken": "next",
                "EntitySummaryList": [
                    {
                        "EntityId": "prod-1",
                        "AmiProductSummary": {
                            "ProductTitle": "One",
                            "Visibility": "Public",
                        },
                    },
                    {
                        "EntityId": "prod-2",
                        "AmiProductSummary": {
                            "ProductTitle": "Two",
                            "Visibility": "Limited",
                        },
                    },
                ],
            },
            {
                "EntitySummaryList": [
                    {
                        "EntityId": "prod-3",
                        "AmiProductSummary": {
                            "ProductTitle": "Three",
                            "Visibility": "Public",
                        },
                    }
                ]
            },
        ]

    def list_entities(self, **kwargs):
        self.list_requests.append(kwargs)
        return self.pages.pop(0)

    def describe_entity(self, **kwargs):
        self.describe_requests.append(kwargs)
        entity = kwargs["EntityId"]
        if entity == "prod-1":
            return {
                "LastModifiedDate": "2026-03-02",
                "DetailsDocument": {
                    "Versions": [
                        {
                            "VersionTitle": "1.0",
                            "CreationDate": "2026-01-01T00:00:00Z",
                            "DeliveryOptions": [{"Visibility": "Public", "Sku": "sku-1"}],
                        },
                        {
                            "VersionTitle": "2.0",
                            "CreationDate": "2026-02-01T00:00:00Z",
                            "DeliveryOptions": [{"Visibility": "Restricted"}],
                        },
                        {
                            "VersionTitle": "3.0",
                            "CreationDate": "2026-03-01T00:00:00Z",
                            "DeliveryOptions": [{"Visibility": "Public", "Sku": "sku-1"}],
                        },
                    ]
                },
            }
        if entity == "prod-2":
            return {
                "LastModifiedDate": "2025-12-02T00:00:00Z",
                "DetailsDocument": {
                    "Versions": [
                        {
                            "VersionTitle": "1.0",
                            "CreationDate": "2025-12-01T00:00:00Z",
                            "DeliveryOptions": [{"Visibility": "Public"}],
                        }
                    ]
                },
            }
        return {
            "LastModifiedDate": "2025-11-01T00:00:00Z",
            "DetailsDocument": {"Versions": []},
        }


class AwsProviderTests(unittest.TestCase):
    def test_lists_versions_and_paginates(self) -> None:
        client = FakeClient()
        provider = offers.AwsMarketplaceProvider(
            client=client, target_versions={"sku-1": "5.0"}
        )

        result = provider.list_offers()

        self.assertEqual([offer.entity_id for offer in result], ["prod-1", "prod-3"])
        by_id = {offer.entity_id: offer for offer in result}
        self.assertEqual(by_id["prod-1"].version, "3.0")
        self.assertEqual(by_id["prod-1"].last_modified, "2026-03-02")
        self.assertEqual(by_id["prod-3"].version, "")
        self.assertEqual(by_id["prod-1"].target_version, "5.0")
        self.assertEqual(by_id["prod-3"].target_version, "")
        self.assertEqual(client.list_requests[0].get("NextToken"), None)
        self.assertEqual(client.list_requests[1].get("NextToken"), "next")
        self.assertEqual(len(client.describe_requests), 2)

    def test_render_markdown_includes_versions_and_note(self) -> None:
        provider = offers.AwsMarketplaceProvider(
            client=FakeClient(), target_versions={"sku-1": "5.0"}
        )
        markdown = offers.render_markdown(provider, provider.list_offers())

        self.assertIn(
            "| Catalog Entity ID | Product title | Visibility | Offer Version | Target Version | Update Suggestion | Update Time |",
            markdown,
        )
        self.assertIn(
            "| [prod-1](https://aws.amazon.com/marketplace/pp?sku=sku-1) | One | Public | "
            "3.0 | 5.0 | Need Update | 2026-03-02 |",
            markdown,
        )
        self.assertIn(
            "| prod-3 | Three | Public | - | - | - | 2025-11-01 |",
            markdown,
        )
        self.assertIn("Only products with `Visibility=Public` are listed.", markdown)

    def test_describe_permission_error_is_actionable(self) -> None:
        client = FakeClient()

        def deny(**kwargs):
            raise AccessDeniedException()

        client.describe_entity = deny
        provider = offers.AwsMarketplaceProvider(client=client)

        with self.assertRaisesRegex(offers.MarketplaceError, "DescribeEntity.*AmiProduct"):
            provider.list_offers()

    def test_list_permission_error_is_actionable(self) -> None:
        client = FakeClient()

        def deny(**kwargs):
            raise AccessDeniedException()

        client.list_entities = deny
        provider = offers.AwsMarketplaceProvider(client=client)

        with self.assertRaisesRegex(offers.MarketplaceError, "ListEntities"):
            provider.list_offers()


class FakeAliyunRequest:
    def __init__(self) -> None:
        self.page_number = 0
        self.page_size = 0
        self.filters = []

    def set_PageNumber(self, value):
        self.page_number = value

    def set_PageSize(self, value):
        self.page_size = value

    def set_Filters(self, value):
        self.filters = value

    def set_accept_format(self, value):
        self.accept_format = value


class FakeAliyunClient:
    def __init__(self) -> None:
        self.requests = []

    def do_action_with_exception(self, request):
        self.requests.append(request)
        if request.page_number == 1:
            products = [
                {
                    "Code": "cmjj001",
                    "Name": "Moodle",
                    "SupplierName": "长沙网久软件有限公司",
                    "DeliveryWay": "镜像",
                    "ShortDescription": "Moodle 5.2.1 on Ubuntu 24.04",
                },
                {
                    "Code": "cmjj-hidden",
                    "Name": "Hidden",
                    "SupplierName": "长沙网久软件有限公司",
                    "DeliveryWay": "镜像",
                    "ShortDescription": "Hidden 1.0 on Ubuntu 24.04",
                },
            ] + [
                {
                    "Code": f"other-{index}",
                    "Name": f"Other {index}",
                    "SupplierName": "其他公司",
                    "DeliveryWay": "镜像",
                    "ShortDescription": f"Other {index} 9.9 on Ubuntu 24.04",
                }
                for index in range(48)
            ]
            return json.dumps(
                {
                    "PageNumber": 1,
                    "PageSize": 50,
                    "ProductItems": {"ProductItem": products},
                }
            ).encode()
        return '{"PageNumber":2,"PageSize":50,"ProductItems":{"ProductItem":[]}}'


def aliyun_store_opener(codes):
    def opener(request, timeout):
        payload = {
            "success": True,
            "result": {
                "products": [
                    {
                        "shop_name": "长沙网久软件有限公司",
                        "delivery_method": "镜像",
                        "productcode": code,
                    }
                    for code in codes
                ],
                "totalPage": 1,
            },
        }
        return io.BytesIO(json.dumps(payload).encode())

    return opener


class AliyunProviderTests(unittest.TestCase):
    def test_lists_image_products_for_supplier_and_paginates(self) -> None:
        client = FakeAliyunClient()
        provider = offers.AliyunMarketplaceProvider(
            client=client,
            request_factory=FakeAliyunRequest,
            store_opener=aliyun_store_opener(["cmjj001"]),
            detail_lookup=lambda code: {"GmtModified": 1_800_000_000_000},
        )

        result = provider.list_offers()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].entity_id, "cmjj001")
        self.assertEqual(result[0].title, "Moodle")
        self.assertEqual(result[0].supplier, "长沙网久软件有限公司")
        self.assertEqual(result[0].delivery_way, "镜像")
        self.assertEqual(result[0].version, "5.2.1")
        self.assertEqual([request.page_number for request in client.requests], [1, 2])
        self.assertTrue(all(request.page_size == 50 for request in client.requests))
        self.assertTrue(
            all(
                request.filters == [{"Key": "productType", "Value": "MIRROR"}]
                for request in client.requests
            )
        )

    def test_store_pagination_adds_visible_codes(self) -> None:
        def opener(request, timeout):
            page = 1 if "pageIndex=1" in request.full_url else 2
            codes = ["cmjj001"] if page == 1 else ["cmjj-hidden"]
            payload = {
                "success": True,
                "result": {
                    "products": [
                        {
                            "shop_name": "长沙网久软件有限公司",
                            "delivery_method": "镜像",
                            "productcode": code,
                        }
                        for code in codes
                    ],
                    "totalPage": 2,
                },
            }
            return io.BytesIO(json.dumps(payload).encode())

        provider = offers.AliyunMarketplaceProvider(
            client=FakeAliyunClient(),
            request_factory=FakeAliyunRequest,
            store_opener=opener,
            detail_lookup=lambda code: {"GmtModified": 1_800_000_000_000},
        )

        result = provider.list_offers()

        self.assertEqual([offer.entity_id for offer in result], ["cmjj001", "cmjj-hidden"])

    def test_store_failure_fails_closed(self) -> None:
        def failing_opener(request, timeout):
            raise OSError("network down")

        provider = offers.AliyunMarketplaceProvider(
            client=FakeAliyunClient(),
            request_factory=FakeAliyunRequest,
            store_opener=failing_opener,
        )

        with self.assertRaisesRegex(offers.MarketplaceError, "front-end visibility"):
            provider.list_offers()

    def test_empty_product_items_is_not_an_error(self) -> None:
        class EmptyClient:
            def do_action_with_exception(self, request):
                return '{"Result":{}}'

        provider = offers.AliyunMarketplaceProvider(
            client=EmptyClient(),
            request_factory=FakeAliyunRequest,
            store_opener=aliyun_store_opener([]),
        )

        self.assertEqual(provider.list_offers(), [])

    def test_render_lists_application_versions(self) -> None:
        provider = offers.AliyunMarketplaceProvider(
            client=FakeAliyunClient(),
            request_factory=FakeAliyunRequest,
            store_opener=aliyun_store_opener(["cmjj001"]),
            target_versions={"cmjj001": "5.3"},
            detail_lookup=lambda code: {"GmtModified": 1_800_000_000_000},
        )

        markdown = offers.render_markdown(provider, provider.list_offers())

        self.assertIn(
            "| Product code | Product title | Short Description | Offer Version | Target Version | Update Suggestion | Update Time |",
            markdown,
        )
        self.assertIn(
            "| [cmjj001](https://market.aliyun.com/detail/cmjj001) | Moodle | "
            "Moodle 5.2.1 on Ubuntu 24.04 | 5.2.1 | 5.3 | Need Update | 2027-01-15 |",
            markdown,
        )
        self.assertIn("Only front-end visible image products", markdown)
        self.assertIn("长沙网久软件有限公司", markdown)

    def test_unidentified_version_is_not_guessed(self) -> None:
        provider = offers.AliyunMarketplaceProvider(
            client=FakeAliyunClient(),
            request_factory=FakeAliyunRequest,
        )

        markdown = offers.render_markdown(
            provider,
            [
                offers.Offer(
                    entity_id="cmjj002",
                    title="Moodle",
                    visibility="",
                    version="未识别",
                    last_modified="",
                    supplier=provider.supplier,
                    delivery_way="镜像",
                    target_version="5.3",
                    product_url="https://market.aliyun.com/detail/cmjj002",
                )
            ],
        )

        self.assertIn(
            "| [cmjj002](https://market.aliyun.com/detail/cmjj002) | Moodle | - | "
            "未识别 | 5.3 | - | - |",
            markdown,
        )

    def test_aliyun_is_registered_as_provider(self) -> None:
        self.assertIs(offers.PROVIDERS["aliyun"], offers.AliyunMarketplaceProvider)
        self.assertIs(
            offers.PROVIDERS["alibabacloud"],
            offers.AlibabaCloudMarketplaceProvider,
        )

    def test_cli_uses_aliyun_region_by_default(self) -> None:
        provider = AliyunProviderSpy()

        def provider_factory(region: str, **kwargs):
            provider.region = region
            return provider

        with patch.dict(offers.PROVIDERS, {"aliyun": provider_factory}):
            self.assertEqual(offers.main(["--provider", "aliyun"]), 0)
        self.assertEqual(provider.region, "cn-hangzhou")


class AlibabaCloudResponse(io.BytesIO):
    pass


class AlibabaCloudProviderTests(unittest.TestCase):
    def _response(self, products: list[dict], total_pages: int) -> bytes:
        return json.dumps(
            {
                "success": True,
                "result": {
                    "product": products,
                    "totalPage": total_pages,
                },
            }
        ).encode()

    @staticmethod
    def _product(
        code: str,
        title: str,
        description: str,
        *,
        company: str = "Websoft9",
        delivery: str = "Image",
    ) -> dict:
        return {
            "productInfo": {
                "code": code,
                "title": title,
                "describe": description,
                "companyName": company,
                "deliveryMethod": delivery,
            }
        }

    def _detail(
        self,
        code: str,
        *,
        latest_version: str = "v5.3",
        last_updated: int = 1_800_000_000_000,
    ) -> dict:
        return {
            "latestVersion": latest_version,
            "lastUpdated": last_updated,
        }

    def test_lists_paginated_websoft9_image_products(self) -> None:
        responses = [
            self._response(
                [
                    self._product("sgcmjj001", "Moodle - Preconfigured", "Moodle v5.2, preconfigured"),
                    self._product("other-supplier", "Other", "Other v1.0", company="Other"),
                    self._product("websoft9-app", "App", "App v2.0", delivery="SaaS"),
                ],
                2,
            ),
            self._response(
                [self._product("sgcmjj002", "Gitea - Preconfigured", "Gitea v1.27, preconfigured")],
                2,
            ),
        ]
        requests = []

        def fake_open(request, timeout):
            requests.append((request, timeout))
            return AlibabaCloudResponse(responses.pop(0))

        provider = offers.AlibabaCloudMarketplaceProvider(
            opener=fake_open,
            detail_lookup=lambda code: self._detail(code),
            version_updates_lookup=lambda code: [],
        )
        result = provider.list_offers()

        self.assertEqual([offer.entity_id for offer in result], ["sgcmjj001", "sgcmjj002"])
        self.assertEqual([offer.version for offer in result], ["5.2", "1.27"])
        self.assertTrue(all(offer.supplier == "Websoft9" for offer in result))
        self.assertTrue(all(offer.delivery_way == "Image" for offer in result))
        self.assertEqual(len(requests), 2)
        self.assertIn("publisherId=2116499", requests[0][0].full_url)
        self.assertIn("curPage=1", requests[0][0].full_url)
        self.assertIn("curPage=2", requests[1][0].full_url)

    def test_render_identifies_provider_and_image_type(self) -> None:
        provider = offers.AlibabaCloudMarketplaceProvider(
            opener=lambda request, timeout: AlibabaCloudResponse(
                self._response(
                    [self._product("sgcmjj001", "Moodle - Preconfigured", "Moodle v5.2, preconfigured")],
                    1,
                )
            ),
            detail_lookup=lambda code: self._detail(code),
            version_updates_lookup=lambda code: [1_820_000_000_000],
            target_versions={"sgcmjj001": "5.4"},
        )

        markdown = offers.render_markdown(provider, provider.list_offers())

        self.assertIn(
            "| Product code | Product title | Short Description | Offer Version | Target Version | Update Suggestion | Update Time |",
            markdown,
        )
        self.assertIn(
            "| [sgcmjj001](https://marketplace.alibabacloud.com/products/201072001/sgcmjj001.html) "
            "| Moodle - Preconfigured | Moodle v5.2, preconfigured | 5.2 | 5.4 | Need Update | 2027-09-03 |",
            markdown,
        )

    def test_update_time_uses_newer_version_timestamp(self) -> None:
        provider = offers.AlibabaCloudMarketplaceProvider(
            opener=lambda request, timeout: AlibabaCloudResponse(
                self._response(
                    [self._product("sgcmjj001", "Moodle", "Moodle v5.2, preconfigured")],
                    1,
                )
            ),
            detail_lookup=lambda code: {
                "latestVersion": "v5.2",
                "lastUpdated": "2026-01-01T00:00:00Z",
            },
            version_updates_lookup=lambda code: [],
        )

        markdown = offers.render_markdown(provider, provider.list_offers())

        self.assertIn("| [sgcmjj001]", markdown)
        self.assertIn("| 2026-01-01 |", markdown)

    def test_update_time_prefers_newer_image_version_timestamp(self) -> None:
        version_opener = lambda request, timeout: AlibabaCloudResponse(
            json.dumps(
                {
                    "success": True,
                    "result": {
                        "versionList": [
                            {"versionName": "v5.3", "updateTime": 1_820_000_000_000}
                        ]
                    },
                }
            ).encode()
        )
        calls = 0

        def opener(request, timeout):
            nonlocal calls
            calls += 1
            if "queryImageVersionInfo.json" in request.full_url:
                return version_opener(request, timeout)
            if "commodityInfo.json" in request.full_url:
                return AlibabaCloudResponse(
                    json.dumps(
                        {
                            "success": True,
                            "result": {
                                "product": {
                                    "commodityInfo": {
                                        "latestVersion": "v5.3",
                                        "lastUpdated": "2026-01-01T00:00:00Z",
                                    }
                                }
                            },
                        }
                    ).encode()
                )
            return AlibabaCloudResponse(
                self._response(
                    [self._product("sgcmjj001", "Moodle", "Moodle v5.3, preconfigured")],
                    1,
                )
            )

        provider = offers.AlibabaCloudMarketplaceProvider(
            opener=opener,
        )

        markdown = offers.render_markdown(provider, provider.list_offers())

        self.assertIn("| 2027-09-03 |", markdown)
        self.assertEqual(calls, 3)

    def test_target_version_maps_product_code_to_versions_source(self) -> None:
        mapping = offers.build_target_versions(
            [
                {
                    "id": "moodle",
                    "type": "app",
                    "productID": {
                        "aliyun": ["cmjj001"],
                        "aws": ["sku-1"],
                    },
                }
            ],
            [{"id": "moodle", "version": "5.3"}],
        )

        self.assertEqual(mapping, {"cmjj001": "5.3", "sku-1": "5.3"})

    def test_alibabacloud_is_registered_and_uses_no_region(self) -> None:
        self.assertIs(
            offers.PROVIDERS["alibabacloud"],
            offers.AlibabaCloudMarketplaceProvider,
        )
        self.assertEqual(offers.AlibabaCloudMarketplaceProvider().region, "")


class SuggestionTests(unittest.TestCase):
    def test_short_description_uses_first_sentence(self) -> None:
        self.assertEqual(
            offers._first_sentence("Moodle 5.2. First sentence. More text."),
            "Moodle 5.2",
        )
        self.assertEqual(
            offers._first_sentence("Moodle 5.2。第二句"),
            "Moodle 5.2",
        )
        self.assertEqual(offers._first_sentence("No punctuation"), "No punctuation")

    def test_update_suggestion_compares_versions(self) -> None:
        self.assertEqual(offers._version_suggestion("5.2.1", "5.3"), "Need Update")
        self.assertEqual(offers._version_suggestion("v5.3", "5.3"), "Up to date")
        self.assertEqual(offers._version_suggestion("5.4", "5.3"), "Check Target")
        self.assertEqual(offers._version_suggestion("未识别", "5.3"), "-")
        self.assertEqual(offers._version_suggestion("5.2", ""), "-")


class IssueAndNotificationTests(unittest.TestCase):
    def test_issue_title_and_body_include_scan_information(self) -> None:
        provider = offers.AlibabaCloudMarketplaceProvider()
        items = [
            offers.Offer(
                entity_id="sgcmjj001",
                title="Moodle",
                visibility="",
                version="5.2",
                last_modified="2026-01-01",
                target_version="5.3",
            )
        ]
        markdown = offers.render_markdown(provider, items)
        self.assertEqual(
            offers._issue_title("alibabacloud", "2026-01-08 10:00 UTC"),
            "Offer list and version - Alibaba Cloud International - 2026-01-08 10:00 UTC",
        )
        body = offers._issue_body(provider, items, markdown, "2026-01-08 10:00 UTC")
        self.assertIn("- Cloud: Alibaba Cloud Marketplace image products", body)
        self.assertIn("- Need Update: 1", body)
        self.assertIn("sgcmjj001", body)

    def test_notification_summarizes_cloud_results(self) -> None:
        message = offers._notification_markdown(
            "2026-01-08 10:00 UTC",
            [
                {
                    "key": "aws",
                    "count": 2,
                    "need_update": 1,
                    "up_to_date": 1,
                    "issue_url": "https://github.com/o/r/issues/1",
                }
            ],
        )
        self.assertIn("**AWS**: 2 products; Need Update 1; Up to date 1", message)
        self.assertIn("https://github.com/o/r/issues/1", message)


class FakeProvider:
    display_name = "Fake Marketplace"
    id_label = "Offer ID"
    note = "Fake note."

    def __init__(self, region: str, **kwargs) -> None:
        self.region = region

    def list_offers(self) -> list[offers.Offer]:
        return [
            offers.Offer(
                entity_id="offer-1",
                title="Example",
                visibility="Public",
                version="1.0",
                last_modified="2026-01-01T00:00:00Z",
            )
        ]


class AliyunProviderSpy:
    display_name = "Aliyun Marketplace products"
    id_label = "Product code"
    note = ""

    def __init__(self) -> None:
        self.region = ""

    def list_offers(self) -> list[offers.Offer]:
        return []


class CliTests(unittest.TestCase):
    def test_writes_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            offers.PROVIDERS, {"aws": FakeProvider}
        ):
            summary = Path(directory) / "summary.md"
            result = offers.main(
                ["--provider", "aws", "--region", "us-east-1", "--summary-file", str(summary)]
            )
            self.assertEqual(result, 0)
            self.assertIn("| offer-1 | Example | Public | 1.0 |", summary.read_text())

    def test_unimplemented_platform_reports_error(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = offers.main(["--provider", "azure"])

        self.assertEqual(result, 1)
        self.assertIn("azure offer listing is not implemented yet", output.getvalue())
        self.assertIn("implemented providers: alibabacloud, aliyun, aws", output.getvalue())

    def test_azure_vmlab_is_selectable_and_reports_unimplemented(self) -> None:
        self.assertIn("azure-vmlab", offers.PLATFORMS)
        output = io.StringIO()
        with redirect_stdout(output):
            result = offers.main(["--provider", "azure-vmlab"])

        self.assertEqual(result, 1)
        self.assertIn("azure-vmlab offer listing is not implemented yet", output.getvalue())

    def test_reports_provider_failure(self) -> None:
        class FailingProvider(FakeProvider):
            def list_offers(self) -> list[offers.Offer]:
                raise offers.MarketplaceError("DescribeEntity permission is required")

        output = io.StringIO()
        with patch.dict(offers.PROVIDERS, {"aws": FailingProvider}), redirect_stdout(output):
            result = offers.main(["--provider", "aws"])

        self.assertEqual(result, 1)
        self.assertIn("::error::DescribeEntity permission is required", output.getvalue())


if __name__ == "__main__":
    unittest.main()
