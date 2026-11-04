#!/usr/bin/env python3
"""List marketplace offers and render a GitHub Actions summary.

Provider-specific API access lives in a small adapter class. Add a new cloud by
implementing another adapter, registering it in PROVIDERS, and adding the key to
PLATFORMS and the workflow input options.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cli.marketplace import (
    OFFER_URL,
    PLATFORM_URL_TEMPLATES,
    VERSIONS_URL,
    load_json,
)
from cli.versioning import extract_marketplace_version


@dataclass(frozen=True)
class Offer:
    entity_id: str
    title: str
    visibility: str
    version: str
    last_modified: str
    supplier: str = ""
    delivery_way: str = ""
    target_version: str = ""
    product_url: str = ""
    summary: str = ""

    @property
    def update_suggestion(self) -> str:
        return _version_suggestion(self.version, self.target_version)


class MarketplaceError(RuntimeError):
    """An actionable marketplace listing failure."""


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) or str(value).strip().isdigit():
            numeric = float(value)
            seconds = numeric / 1000 if numeric > 100_000_000_000 else numeric
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def _latest_update_time(*values: Any) -> str:
    parsed = [timestamp for value in values if (timestamp := _parse_timestamp(value))]
    if not parsed:
        return ""
    return max(parsed).strftime("%Y-%m-%d")


def _first_sentence(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    for match in re.finditer(r"[.。]", text):
        index = match.start()
        if (
            text[index] == "."
            and 0 < index < len(text) - 1
            and text[index - 1].isdigit()
            and text[index + 1].isdigit()
        ):
            continue
        return text[:index].strip()
    return text


def _version_key(value: str) -> tuple[int, ...] | None:
    text = str(value or "").strip().lstrip("vV")
    if not re.search(r"\d", text):
        return None
    prerelease = 0 if re.search(r"(?i)(?:rc|beta|alpha|preview|pre|dev)", text) else 1
    numbers = [int(item) for item in re.findall(r"\d+", text)][:4]
    numbers.extend([0] * (4 - len(numbers)))
    return tuple(numbers) + (prerelease,)


def _version_suggestion(offer_version: str, target_version: str) -> str:
    offer = str(offer_version or "").strip()
    target = str(target_version or "").strip()
    if not offer or not target or offer == "未识别":
        return "-"
    if offer.lstrip("vV").casefold() == target.lstrip("vV").casefold():
        return "Up to date"
    offer_key = _version_key(offer)
    target_key = _version_key(target)
    if offer_key is not None and target_key is not None:
        if target_key > offer_key:
            return "Need Update"
        if target_key < offer_key:
            return "Check Target"
    return "Review"


def build_target_versions(
    offers: Any,
    versions: Any,
) -> dict[str, str]:
    if not isinstance(offers, list) or not isinstance(versions, list):
        return {}
    version_by_app = {
        str(item.get("id")): str(item.get("version") or "").strip()
        for item in versions
        if isinstance(item, dict) and item.get("id") and item.get("version")
    }
    code_to_apps: dict[str, set[str]] = {}
    for item in offers:
        if not isinstance(item, dict) or item.get("type") != "app":
            continue
        app_key = str(item.get("id") or "").strip()
        if not app_key:
            continue
        product_ids = item.get("productID") or {}
        if not isinstance(product_ids, dict):
            continue
        for platform in ("aws", "aliyun", "alibabacloud"):
            codes = product_ids.get(platform) or []
            if not isinstance(codes, list):
                continue
            for code in codes:
                if code:
                    code_to_apps.setdefault(str(code), set()).add(app_key)

    result: dict[str, str] = {}
    for code, app_keys in code_to_apps.items():
        candidates = {version_by_app.get(app_key, "") for app_key in app_keys}
        candidates.discard("")
        if len(candidates) == 1:
            result[code] = next(iter(candidates))
    return result


def load_target_versions() -> dict[str, str]:
    try:
        return build_target_versions(load_json(OFFER_URL), load_json(VERSIONS_URL))
    except Exception as error:
        print(
            f"::warning::Could not load target versions from {VERSIONS_URL} ({type(error).__name__}).",
            file=sys.stderr,
        )
        return {}


def marketplace_product_url(platform: str, code: str) -> str:
    if not code:
        return ""
    template = PLATFORM_URL_TEMPLATES.get(platform, "")
    return template.replace("{code}", urllib.parse.quote(code, safe="")) if template else ""


class MarketplaceProvider(Protocol):
    display_name: str
    id_label: str
    note: str

    def list_offers(self) -> list[Offer]:
        ...


def _error_code(error: Exception) -> str:
    response = getattr(error, "response", None) or {}
    return response.get("Error", {}).get("Code") or type(error).__name__


class AwsMarketplaceProvider:
    display_name = "AWS Marketplace AMI products"
    id_label = "Catalog Entity ID"
    columns = (
        ("Catalog Entity ID", "product_link"),
        ("Product title", "title"),
        ("Visibility", "visibility"),
        ("Offer Version", "version"),
        ("Target Version", "target_version"),
        ("Update Suggestion", "update_suggestion"),
        ("Update Time", "last_modified"),
    )
    note = (
        "Only products with `Visibility=Public` are listed. Version is the latest "
        "public version; Last updated is the product entity's `LastModifiedDate`."
    )

    def __init__(
        self,
        region: str = "us-east-1",
        client: Any | None = None,
        target_versions: dict[str, str] | None = None,
    ) -> None:
        self.region = region
        self._client = client
        self.target_versions = target_versions or {}

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "marketplace-catalog",
                region_name=self.region,
                config=Config(retries={"mode": "standard", "total_max_attempts": 5}),
            )
        return self._client

    def _call(self, operation: str, permission_hint: str, **kwargs: Any) -> dict[str, Any]:
        try:
            return getattr(self.client, operation)(**kwargs)
        except Exception as error:
            code = _error_code(error)
            if code == "AccessDeniedException":
                raise MarketplaceError(permission_hint) from None
            raise MarketplaceError(f"AWS {operation} failed ({code})") from None

    def _describe(self, entity_id: str) -> tuple[str, str, str]:
        response = self._call(
            "describe_entity",
            "DescribeEntity permission is required to list versions. "
            "Allow aws-marketplace:DescribeEntity on AmiProduct/*.",
            Catalog="AWSMarketplace",
            EntityId=entity_id,
        )
        detail = response.get("DetailsDocument")
        if not detail:
            try:
                detail = json.loads(response.get("Details") or "{}")
            except (TypeError, ValueError):
                raise MarketplaceError("DescribeEntity returned malformed details") from None
        if not isinstance(detail, dict):
            raise MarketplaceError("DescribeEntity returned malformed details")

        versions = detail.get("Versions") or []
        public_versions = [
            version
            for version in versions
            if any(
                option.get("Visibility") == "Public"
                for option in (version.get("DeliveryOptions") or [])
            )
        ]
        candidates = public_versions
        if not candidates:
            return "", "", _latest_update_time(response.get("LastModifiedDate"))

        latest = max(candidates, key=lambda version: version.get("CreationDate") or "")
        sku = next(
            (
                str(option.get("Sku") or "")
                for option in (latest.get("DeliveryOptions") or [])
                if option.get("Visibility") == "Public" and option.get("Sku")
            ),
            "",
        )
        return (
            latest.get("VersionTitle") or latest.get("Id") or "",
            sku,
            _latest_update_time(response.get("LastModifiedDate")),
        )

    def list_offers(self) -> list[Offer]:
        token = None
        offers: list[Offer] = []
        while True:
            request = {
                "Catalog": "AWSMarketplace",
                "EntityType": "AmiProduct",
                "MaxResults": 50,
            }
            if token:
                request["NextToken"] = token
            response = self._call(
                "list_entities",
                "ListEntities permission is required to list seller products. "
                "Allow aws-marketplace:ListEntities.",
                **request,
            )
            for entity in response.get("EntitySummaryList", []):
                summary = entity.get("AmiProductSummary") or {}
                if summary.get("Visibility") != "Public":
                    continue
                entity_id = entity.get("EntityId", "")
                version, sku, last_modified = self._describe(entity_id)
                offers.append(
                    Offer(
                        entity_id=entity_id,
                        title=summary.get("ProductTitle") or entity.get("Name", ""),
                        visibility=summary.get("Visibility", ""),
                        version=version,
                        last_modified=last_modified,
                        target_version=self.target_versions.get(sku, ""),
                        product_url=marketplace_product_url("aws", sku),
                    )
                )
            token = response.get("NextToken")
            if not token:
                break
        return offers


class AliyunMarketplaceProvider:
    display_name = "Aliyun Marketplace image products"
    id_label = "Product code"
    supplier = "长沙网久软件有限公司"
    product_type = "MIRROR"
    store_id = "228399"
    store_api = "https://market.aliyun.com/api/ajax/product/queryProducts.json"
    page_size = 50
    columns = (
        ("Product code", "product_link"),
        ("Product title", "title"),
        ("Short Description", "summary"),
        ("Offer Version", "version"),
        ("Target Version", "target_version"),
        ("Update Suggestion", "update_suggestion"),
        ("Update Time", "last_modified"),
    )
    note = (
        "Only front-end visible image products (`productType=MIRROR`) from supplier "
        f"`{supplier}` are listed. `未识别` means no application version could be "
        "confirmed from the product summary."
    )

    def __init__(
        self,
        region: str = "cn-hangzhou",
        client: Any | None = None,
        request_factory: Any | None = None,
        store_opener: Any | None = None,
        target_versions: dict[str, str] | None = None,
        detail_lookup: Any | None = None,
    ) -> None:
        self.region = region
        self._client = client
        self._request_factory = request_factory
        self._store_opener = store_opener or urllib.request.urlopen
        self.target_versions = target_versions or {}
        self._detail_lookup = detail_lookup

    def _fetch_product_updated_at(self, code: str) -> Any:
        if self._detail_lookup is not None:
            try:
                detail = self._detail_lookup(code)
            except Exception as error:
                raise MarketplaceError(
                    f"Aliyun Market DescribeProduct failed for {code} "
                    f"({type(error).__name__})"
                ) from None
            result = detail.get("Result", detail) if isinstance(detail, dict) else {}
            return result.get("GmtModified") if isinstance(result, dict) else None

        try:
            from aliyunsdkmarket.request.v20151101.DescribeProductRequest import (
                DescribeProductRequest,
            )
        except ImportError as error:
            raise MarketplaceError(
                "install the Aliyun SDK with: pip install aliyun-python-sdk-core "
                "aliyun-python-sdk-market"
            ) from error

        request = DescribeProductRequest()
        request.set_Code(code)
        request.set_QueryDraft(False)
        try:
            response = self._client.do_action_with_exception(request)
            parsed = json.loads(
                response.decode("utf-8") if isinstance(response, bytes) else response
            )
        except Exception as error:
            raise MarketplaceError(
                f"Aliyun Market DescribeProduct failed for {code} "
                f"({type(error).__name__})"
            ) from None
        result = parsed.get("Result", parsed) if isinstance(parsed, dict) else {}
        return result.get("GmtModified") if isinstance(result, dict) else None

    def _fetch_visible_products(self) -> dict[str, dict[str, Any]]:
        visible: dict[str, dict[str, Any]] = {}
        page = 1
        total_pages = 1
        while page <= total_pages:
            query = urllib.parse.urlencode(
                {
                    "supplierId": self.store_id,
                    "pageIndex": page,
                    "pageSize": self.page_size,
                }
            )
            request = urllib.request.Request(
                f"{self.store_api}?{query}",
                headers={
                    "User-Agent": "Websoft9-marketplace-offer-list/1.0",
                    "Referer": f"https://market.aliyun.com/store/{self.store_id}/index.html",
                },
            )
            try:
                with self._store_opener(request, timeout=30) as response:
                    payload = response.read()
            except Exception as error:
                raise MarketplaceError(
                    "Aliyun Marketplace store query failed "
                    f"({type(error).__name__}); cannot verify front-end visibility"
                ) from None

            try:
                parsed = json.loads(payload)
            except (TypeError, ValueError, UnicodeDecodeError):
                raise MarketplaceError(
                    "Aliyun Marketplace store query returned invalid JSON"
                ) from None
            if not isinstance(parsed, dict) or parsed.get("success") is not True:
                raise MarketplaceError("Aliyun Marketplace store query failed")
            result = parsed.get("result")
            if not isinstance(result, dict):
                raise MarketplaceError("Aliyun Marketplace store query is missing result data")
            products = result.get("products")
            if not isinstance(products, list):
                raise MarketplaceError("Aliyun Marketplace store query has malformed product data")
            try:
                total_pages = int(result.get("totalPage") or 1)
            except (TypeError, ValueError):
                raise MarketplaceError(
                    "Aliyun Marketplace store query has invalid pagination data"
                ) from None
            if total_pages < 0 or total_pages > 1000:
                raise MarketplaceError(
                    "Aliyun Marketplace store query has invalid pagination data"
                )

            for product in products:
                if not isinstance(product, dict):
                    continue
                supplier = str(product.get("shop_name") or "").strip()
                delivery = str(product.get("delivery_method") or "").strip()
                code = str(product.get("productcode") or "").strip()
                if supplier == self.supplier and delivery == "镜像" and code:
                    visible[code] = product
            page += 1
        return visible

    def _initialize(self) -> None:
        if self._client is not None and self._request_factory is not None:
            return
        try:
            if self._request_factory is None:
                from aliyunsdkmarket.request.v20151101.DescribeProductsRequest import (
                    DescribeProductsRequest,
                )
                self._request_factory = DescribeProductsRequest
            if self._client is None:
                from aliyunsdkcore.auth.credentials import StsTokenCredential
                from aliyunsdkcore.client import AcsClient
        except ImportError as error:
            raise MarketplaceError(
                "install the Aliyun SDK with: pip install aliyun-python-sdk-core "
                "aliyun-python-sdk-market"
            ) from error
        if self._client is None:
            access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip()
            access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "").strip()
            security_token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN", "").strip()
            if not access_key_id or not access_key_secret:
                raise MarketplaceError(
                    "Aliyun OIDC credentials are missing; configure the GitHub Actions OIDC "
                    "step to provide ALIBABA_CLOUD_ACCESS_KEY_ID, "
                    "ALIBABA_CLOUD_ACCESS_KEY_SECRET, and "
                    "ALIBABA_CLOUD_SECURITY_TOKEN"
                )
            credential = None
            if security_token:
                credential = StsTokenCredential(
                    sts_access_key_id=access_key_id,
                    sts_access_key_secret=access_key_secret,
                    sts_token=security_token,
                )
            self._client = AcsClient(
                access_key_id if credential is None else None,
                access_key_secret if credential is None else None,
                region_id=self.region,
                credential=credential,
                timeout=30,
            )

    def list_offers(self) -> list[Offer]:
        visible_products = self._fetch_visible_products()
        self._initialize()
        page_number = 1
        page_size = self.page_size
        offers: list[Offer] = []
        while True:
            request = self._request_factory()
            request.set_PageNumber(page_number)
            request.set_PageSize(page_size)
            request.set_Filters([{"Key": "productType", "Value": self.product_type}])
            request.set_accept_format("json")
            try:
                response = self._client.do_action_with_exception(request)
            except Exception as error:
                raise MarketplaceError(
                    "Aliyun Market DescribeProducts failed "
                    f"({type(error).__name__}); verify the RAM role allows the "
                    "DescribeProducts API"
                ) from None

            try:
                if isinstance(response, bytes):
                    response = response.decode("utf-8")
                parsed = json.loads(response) if isinstance(response, str) else response
            except (TypeError, ValueError, UnicodeDecodeError):
                raise MarketplaceError("Aliyun DescribeProducts returned invalid JSON") from None
            if not isinstance(parsed, dict):
                raise MarketplaceError("Aliyun DescribeProducts returned an unexpected response")
            if parsed.get("Code"):
                raise MarketplaceError(
                    "Aliyun Market DescribeProducts returned API error "
                    f"({parsed.get('Code')})"
                )

            result = parsed.get("Result", parsed)
            if not isinstance(result, dict):
                raise MarketplaceError("Aliyun DescribeProducts returned an unexpected response")
            product_items = result.get("ProductItems") or {}
            if not isinstance(product_items, dict):
                raise MarketplaceError("Aliyun DescribeProducts returned malformed ProductItems")
            products = product_items.get("ProductItem") or []
            if isinstance(products, dict):
                products = [products]
            if not isinstance(products, list):
                raise MarketplaceError("Aliyun DescribeProducts returned malformed product items")

            for product in products:
                if not isinstance(product, dict):
                    continue
                supplier = str(product.get("SupplierName") or "").strip()
                code = str(product.get("Code") or "").strip()
                store_product = visible_products.get(code)
                if supplier != self.supplier or store_product is None:
                    continue
                title = str(product.get("Name") or "")
                summary = str(product.get("ShortDescription") or "")
                store_summary = str(store_product.get("short_description") or "")
                offer_version = (
                    extract_marketplace_version(summary, title)
                    or extract_marketplace_version(store_summary, title)
                    or "未识别"
                )
                update_time = _latest_update_time(
                    store_product.get("updateOn"),
                    self._fetch_product_updated_at(code),
                )
                offers.append(
                    Offer(
                        entity_id=code,
                        title=title,
                        visibility="",
                        version=offer_version,
                        last_modified=update_time,
                        supplier=supplier,
                        delivery_way=str(product.get("DeliveryWay") or ""),
                        target_version=self.target_versions.get(code, ""),
                        product_url=marketplace_product_url("aliyun", code),
                        summary=_first_sentence(summary or store_summary),
                    )
                )
            if len(products) < page_size:
                break
            page_number += 1
        return offers

class AlibabaCloudMarketplaceProvider:
    display_name = "Alibaba Cloud Marketplace image products"
    id_label = "Product code"
    supplier = "Websoft9"
    delivery_method = "Image"
    store_id = "2116499"
    page_size = 20
    columns = (
        ("Product code", "product_link"),
        ("Product title", "title"),
        ("Short Description", "summary"),
        ("Offer Version", "version"),
        ("Target Version", "target_version"),
        ("Update Suggestion", "update_suggestion"),
        ("Update Time", "last_modified"),
    )
    note = (
        "Only image products (`deliveryMethod=Image`) from the Websoft9 Alibaba Cloud store "
        f"({store_id}) are listed. The application version is extracted from the product "
        "description; `未识别` means no application version could be confirmed."
    )

    def __init__(
        self,
        region: str = "",
        opener: Any | None = None,
        detail_lookup: Any | None = None,
        version_updates_lookup: Any | None = None,
        target_versions: dict[str, str] | None = None,
    ) -> None:
        self.region = region
        self._opener = opener or urllib.request.urlopen
        self._detail_lookup = detail_lookup
        self._version_updates_lookup = version_updates_lookup
        self.target_versions = target_versions or {}

    def _fetch_product_detail(self, code: str) -> dict[str, Any]:
        if self._detail_lookup is not None:
            try:
                result = self._detail_lookup(code)
            except Exception as error:
                raise MarketplaceError(
                    f"Alibaba Cloud Marketplace product detail query failed "
                    f"for {code} ({type(error).__name__})"
                ) from None
            if not isinstance(result, dict):
                raise MarketplaceError("Alibaba Cloud Marketplace returned malformed product detail")
            return result

        query = urllib.parse.urlencode({"commodityCode": code})
        request = urllib.request.Request(
            f"https://marketplace.alibabacloud.com/api/ajax/newCommodityDetail/commodityInfo.json?{query}",
            headers={
                "User-Agent": "Websoft9-marketplace-offer-list/1.0",
                "Referer": f"https://marketplace.alibabacloud.com/products/201072001/{urllib.parse.quote(code, safe='')}.html",
                "Accept": "application/json, text/plain, */*",
            },
        )
        try:
            with self._opener(request, timeout=30) as response:
                payload = response.read()
            parsed = json.loads(payload)
        except Exception as error:
            raise MarketplaceError(
                f"Alibaba Cloud Marketplace product detail query failed "
                f"for {code} ({type(error).__name__})"
            ) from None
        if not isinstance(parsed, dict) or parsed.get("success") is not True:
            raise MarketplaceError(f"Alibaba Cloud Marketplace product detail unavailable for {code}")
        result = parsed.get("result") or {}
        product = result.get("product") or {}
        if not isinstance(product, dict):
            raise MarketplaceError(f"Alibaba Cloud Marketplace returned malformed detail for {code}")
        commodity = product.get("commodityInfo") or {}
        if not isinstance(commodity, dict):
            raise MarketplaceError(f"Alibaba Cloud Marketplace returned malformed detail for {code}")
        return commodity

    def _fetch_version_update_times(self, code: str) -> list[Any]:
        if self._version_updates_lookup is not None:
            try:
                result = self._version_updates_lookup(code)
            except Exception as error:
                raise MarketplaceError(
                    f"Alibaba Cloud Marketplace version query failed "
                    f"for {code} ({type(error).__name__})"
                ) from None
            if result is None:
                return []
            return result if isinstance(result, list) else [result]

        query = urllib.parse.urlencode({"commodityCode": code})
        request = urllib.request.Request(
            "https://marketplace.alibabacloud.com/api/ajax/newCommodityDetail/"
            f"queryImageVersionInfo.json?{query}",
            headers={
                "User-Agent": "Websoft9-marketplace-offer-list/1.0",
                "Referer": f"https://marketplace.alibabacloud.com/products/201072001/{urllib.parse.quote(code, safe='')}.html",
                "Accept": "application/json, text/plain, */*",
            },
        )
        try:
            with self._opener(request, timeout=30) as response:
                parsed = json.loads(response.read())
        except Exception as error:
            raise MarketplaceError(
                f"Alibaba Cloud Marketplace image version query failed "
                f"for {code} ({type(error).__name__})"
            ) from None
        if not isinstance(parsed, dict) or parsed.get("success") is not True:
            raise MarketplaceError(f"Alibaba Cloud Marketplace image versions unavailable for {code}")
        versions = (parsed.get("result") or {}).get("versionList") or []
        if not isinstance(versions, list):
            raise MarketplaceError(f"Alibaba Cloud Marketplace returned malformed versions for {code}")
        return [
            timestamp
            for item in versions
            if isinstance(item, dict)
            for timestamp in (item.get("updateTime"), item.get("lastUpdated"))
            if timestamp
        ]

    def _fetch_page(self, page: int) -> dict[str, Any]:
        query = urllib.parse.urlencode(
            {
                "order": "NewListing",
                "curPage": page,
                "keywords": "",
                "pageSize": self.page_size,
                "publisherId": self.store_id,
            }
        )
        request = urllib.request.Request(
            f"https://marketplace.alibabacloud.com/api/ajax/newCommodityList/queryNewList.json?{query}",
            headers={
                "User-Agent": "Websoft9-marketplace-offer-list/1.0",
                "Referer": f"https://marketplace.alibabacloud.com/store/{self.store_id}.html",
            },
        )
        try:
            with self._opener(request, timeout=30) as response:
                payload = response.read()
        except Exception as error:
            raise MarketplaceError(
                f"Alibaba Cloud Marketplace store query failed ({type(error).__name__})"
            ) from None

        try:
            parsed = json.loads(payload)
        except (TypeError, ValueError, UnicodeDecodeError):
            raise MarketplaceError("Alibaba Cloud Marketplace returned invalid JSON") from None
        if not isinstance(parsed, dict):
            raise MarketplaceError("Alibaba Cloud Marketplace returned an unexpected response")
        if parsed.get("success") is not True:
            code = parsed.get("code") or "unknown error"
            raise MarketplaceError(f"Alibaba Cloud Marketplace store query failed ({code})")
        result = parsed.get("result")
        if not isinstance(result, dict):
            raise MarketplaceError("Alibaba Cloud Marketplace response is missing result data")
        if not isinstance(result.get("product"), list):
            raise MarketplaceError("Alibaba Cloud Marketplace response has malformed product data")
        try:
            total_pages = int(result["totalPage"])
        except (KeyError, TypeError, ValueError):
            raise MarketplaceError("Alibaba Cloud Marketplace response is missing pagination data") from None
        if total_pages < 0:
            raise MarketplaceError("Alibaba Cloud Marketplace response has invalid pagination data")
        result["totalPage"] = total_pages
        return result

    def list_offers(self) -> list[Offer]:
        offers: list[Offer] = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            result = self._fetch_page(page)
            total_pages = result["totalPage"]
            for item in result["product"]:
                if not isinstance(item, dict):
                    continue
                product = item.get("productInfo")
                if not isinstance(product, dict):
                    continue
                supplier = str(product.get("companyName") or "").strip()
                delivery_method = str(product.get("deliveryMethod") or "").strip()
                if supplier != self.supplier or delivery_method != self.delivery_method:
                    continue
                title = str(product.get("title") or "")
                description = str(product.get("describe") or "")
                app_name = title.split(" - ", maxsplit=1)[0]
                version = extract_marketplace_version(description, title, app_name) or "未识别"
                code = str(product.get("code") or "")
                detail = self._fetch_product_detail(code)
                detail_version = str(detail.get("latestVersion") or "").strip()
                if detail_version and version == "未识别":
                    version = detail_version.lstrip("vV")
                version_updates = self._fetch_version_update_times(code)
                update_time = _latest_update_time(detail.get("lastUpdated"), *version_updates)
                offers.append(
                    Offer(
                        entity_id=code,
                        title=title,
                        visibility="",
                        version=version,
                        last_modified=update_time,
                        supplier=supplier,
                        delivery_way=delivery_method,
                        target_version=self.target_versions.get(code, ""),
                        product_url=marketplace_product_url("alibabacloud", code),
                        summary=_first_sentence(description),
                    )
                )
            page += 1
        return offers


PLATFORMS = (
    "aws",
    "azure",
    "azure-vmlab",
    "alibabacloud",
    "aliyun",
    "huaweicloud",
    "huaweiyun",
    "googlecloud",
)

PROVIDERS: dict[str, type[MarketplaceProvider]] = {
    "aws": AwsMarketplaceProvider,
    "alibabacloud": AlibabaCloudMarketplaceProvider,
    "aliyun": AliyunMarketplaceProvider,
}


def _cell(value: str) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def render_markdown(provider: MarketplaceProvider, offers: list[Offer]) -> str:
    columns = getattr(
        provider,
        "columns",
        (
            (provider.id_label, "entity_id"),
            ("Product title", "title"),
            ("Visibility", "visibility"),
            ("Version", "version"),
            ("Last updated", "last_modified"),
        ),
    )
    headers = [label for label, _ in columns]
    lines = [
        f"## {provider.display_name}",
        "",
        f"Found **{len(offers)}** offer(s) in the connected account.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for offer in sorted(offers, key=lambda item: (item.title.casefold(), item.entity_id)):
        cells = []
        for _, field in columns:
            if field == "product_link":
                value = (
                    f"[{_cell(offer.entity_id)}]({offer.product_url})"
                    if offer.product_url
                    else _cell(offer.entity_id or "-")
                )
            else:
                value = _cell(getattr(offer, field) or "-")
            cells.append(value)
        lines.append("| " + " | ".join(cells) + " |")
    if provider.note:
        lines.extend(["", f"> {provider.note}"])
    return "\n".join(lines) + "\n"


def _summary_path(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    configured = os.environ.get("GITHUB_STEP_SUMMARY")
    return Path(configured) if configured else None


ALL_PROVIDER_KEYS = ("aws", "aliyun", "alibabacloud")
CLOUD_LABELS = {
    "aws": "AWS",
    "aliyun": "Aliyun China",
    "alibabacloud": "Alibaba Cloud International",
}


def _provider_default_region(key: str) -> str:
    return {
        "aws": "us-east-1",
        "aliyun": "cn-hangzhou",
        "alibabacloud": "",
    }.get(key, "us-east-1")


def _build_provider(key: str, region: str | None, target_versions: dict[str, str]) -> MarketplaceProvider:
    provider_class = PROVIDERS[key]
    kwargs: dict[str, Any] = {"region": region or _provider_default_region(key)}
    if key in ALL_PROVIDER_KEYS:
        kwargs["target_versions"] = target_versions
    return provider_class(**kwargs)


def _scan_time() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _issue_title(key: str, scan_time: str) -> str:
    return f"Offer list and version - {CLOUD_LABELS.get(key, key)} - {scan_time}"


def _issue_body(provider: MarketplaceProvider, offers: list[Offer], markdown: str, scan_time: str) -> str:
    need_update = sum(1 for offer in offers if offer.update_suggestion == "Need Update")
    up_to_date = sum(1 for offer in offers if offer.update_suggestion == "Up to date")
    check_target = sum(1 for offer in offers if offer.update_suggestion == "Check Target")
    review = sum(1 for offer in offers if offer.update_suggestion == "Review")
    missing = sum(
        1
        for offer in offers
        if not offer.version or not offer.target_version or offer.version == "未识别"
    )
    return "\n".join(
        [
            "## Offer list and version",
            "",
            f"- Cloud: {provider.display_name}",
            f"- Scan time: {scan_time}",
            f"- Products: {len(offers)}",
            f"- Need Update: {need_update}",
            f"- Up to date: {up_to_date}",
            f"- Check Target: {check_target}",
            f"- Review: {review}",
            f"- Missing version: {missing}",
            "",
            markdown,
        ]
    )


def _create_github_issue(title: str, body: str) -> str:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not repository or not token:
        raise MarketplaceError("GITHUB_REPOSITORY and GITHUB_TOKEN are required to create issues")
    payload = json.dumps({"title": title, "body": body}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/issues",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise MarketplaceError(f"issue creation failed ({error.code})") from None
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise MarketplaceError(f"issue creation failed ({type(error).__name__})") from None
    return str(result.get("html_url") or "")


def _notification_markdown(scan_time: str, results: list[dict[str, Any]]) -> str:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run_url = os.environ.get("RUN_URL", "")
    lines = [
        "# Marketplace Offer List",
        f"> Scan time: {scan_time}",
        f"> Repository: {repository}",
    ]
    for result in results:
        label = CLOUD_LABELS.get(result["key"], result["key"])
        if result.get("error"):
            lines.append(f"> **{label}**: failed - {result['error']}")
            continue
        line = (
            f"> **{label}**: {result['count']} products; "
            f"Need Update {result['need_update']}; Up to date {result['up_to_date']}"
        )
        if result.get("issue_url"):
            line += f"; [Issue]({result['issue_url']})"
        lines.append(line)
    if run_url:
        lines.extend(["", f"[View workflow run]({run_url})"])
    return "\n".join(lines) + "\n"


def _write_notification(path: Path | None, content: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List marketplace offers and render a GitHub Actions summary."
    )
    parser.add_argument("--provider", choices=(*PLATFORMS, "all"), default="all")
    parser.add_argument("--region")
    parser.add_argument("--summary-file", type=Path)
    parser.add_argument("--create-issue", action="store_true")
    parser.add_argument("--notification-file", type=Path)
    args = parser.parse_args(argv)

    selected = ALL_PROVIDER_KEYS if args.provider == "all" else (args.provider,)
    if args.provider != "all" and args.provider not in PROVIDERS:
        print(
            f"::error::{args.provider} offer listing is not implemented yet; "
            f"implemented providers: {', '.join(sorted(PROVIDERS))}"
        )
        return 1

    scan_time = _scan_time()
    target_versions = load_target_versions()
    summary = _summary_path(args.summary_file)
    if summary:
        summary.parent.mkdir(parents=True, exist_ok=True)
    all_markdown: list[str] = []
    results: list[dict[str, Any]] = []
    exit_code = 0

    for key in selected:
        if key not in PROVIDERS:
            print(
                f"::error::{key} offer listing is not implemented yet; "
                f"implemented providers: {', '.join(sorted(PROVIDERS))}"
            )
            results.append({"key": key, "error": "not implemented"})
            exit_code = 1
            continue
        try:
            provider = _build_provider(
                key,
                None if args.provider == "all" else args.region,
                target_versions,
            )
            offers = provider.list_offers()
            markdown = render_markdown(provider, offers)
            all_markdown.append(markdown)
            issue_url = ""
            if args.create_issue:
                issue_url = _create_github_issue(
                    _issue_title(key, scan_time),
                    _issue_body(provider, offers, markdown, scan_time),
                )
            results.append(
                {
                    "key": key,
                    "count": len(offers),
                    "need_update": sum(
                        1 for offer in offers if offer.update_suggestion == "Need Update"
                    ),
                    "up_to_date": sum(
                        1 for offer in offers if offer.update_suggestion == "Up to date"
                    ),
                    "issue_url": issue_url,
                }
            )
            print(
                f"Listed {len(offers)} {key} offer(s)."
                + (f" Issue: {issue_url}" if issue_url else ""),
                file=sys.stderr,
            )
        except MarketplaceError as error:
            print(f"::error::{error}")
            results.append({"key": key, "error": str(error)})
            exit_code = 1

    markdown = "\n".join(all_markdown)
    if summary and markdown:
        with summary.open("a", encoding="utf-8") as file:
            file.write(markdown)
    elif markdown:
        print(markdown, end="")
    _write_notification(args.notification_file, _notification_markdown(scan_time, results))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
