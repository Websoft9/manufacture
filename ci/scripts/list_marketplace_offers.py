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
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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


class MarketplaceError(RuntimeError):
    """An actionable marketplace listing failure."""


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
    note = (
        "Version is the latest public version (or latest version if none is public); "
        "Last updated is the product entity's `LastModifiedDate`."
    )

    def __init__(self, region: str = "us-east-1", client: Any | None = None) -> None:
        self.region = region
        self._client = client

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

    def _describe(self, entity_id: str) -> tuple[str, str]:
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
        candidates = public_versions or versions
        if not candidates:
            return "", response.get("LastModifiedDate", "")

        latest = max(candidates, key=lambda version: version.get("CreationDate") or "")
        return (
            latest.get("VersionTitle") or latest.get("Id") or "",
            response.get("LastModifiedDate", ""),
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
                entity_id = entity.get("EntityId", "")
                version, last_modified = self._describe(entity_id)
                offers.append(
                    Offer(
                        entity_id=entity_id,
                        title=summary.get("ProductTitle") or entity.get("Name", ""),
                        visibility=summary.get("Visibility", ""),
                        version=version,
                        last_modified=last_modified,
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
        ("Product code", "entity_id"),
        ("Product title", "title"),
        ("Application version", "version"),
        ("Delivery way", "delivery_way"),
    )
    note = (
        "Only front-end visible image products (`productType=MIRROR`) from supplier "
        f"`{supplier}` are listed. The application version is extracted from "
        "`ShortDescription`; `未识别` means no version could be confirmed in the summary."
    )

    def __init__(
        self,
        region: str = "cn-hangzhou",
        client: Any | None = None,
        request_factory: Any | None = None,
        store_opener: Any | None = None,
    ) -> None:
        self.region = region
        self._client = client
        self._request_factory = request_factory
        self._store_opener = store_opener or urllib.request.urlopen

    def _fetch_visible_product_codes(self) -> set[str]:
        codes: set[str] = set()
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
                    codes.add(code)
            page += 1
        return codes

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
        visible_codes = self._fetch_visible_product_codes()
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
                if supplier != self.supplier or code not in visible_codes:
                    continue
                title = str(product.get("Name") or "")
                summary = str(product.get("ShortDescription") or "")
                offers.append(
                    Offer(
                        entity_id=code,
                        title=title,
                        visibility="",
                        version=extract_marketplace_version(summary, title) or "未识别",
                        last_modified="",
                        supplier=supplier,
                        delivery_way=str(product.get("DeliveryWay") or ""),
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
        ("Product code", "entity_id"),
        ("Product title", "title"),
        ("Provider", "supplier"),
        ("Product type", "delivery_way"),
        ("Application version", "version"),
    )
    note = (
        "Only image products (`deliveryMethod=Image`) from the Websoft9 Alibaba Cloud store "
        f"({store_id}) are listed. The application version is extracted from the product "
        "description; `未识别` means no application version could be confirmed."
    )

    def __init__(self, region: str = "", opener: Any | None = None) -> None:
        self.region = region
        self._opener = opener or urllib.request.urlopen

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
                offers.append(
                    Offer(
                        entity_id=str(product.get("code") or ""),
                        title=title,
                        visibility="",
                        version=version,
                        last_modified="",
                        supplier=supplier,
                        delivery_way=delivery_method,
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
        cells = [_cell(getattr(offer, field) or "-") for _, field in columns]
        lines.append("| " + " | ".join(cells) + " |")
    if provider.note:
        lines.extend(["", f"> {provider.note}"])
    return "\n".join(lines) + "\n"


def _summary_path(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    configured = os.environ.get("GITHUB_STEP_SUMMARY")
    return Path(configured) if configured else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List marketplace offers and render a GitHub Actions summary."
    )
    parser.add_argument("--provider", choices=PLATFORMS, default="aws")
    parser.add_argument("--region")
    parser.add_argument("--summary-file", type=Path)
    args = parser.parse_args(argv)

    if args.provider not in PROVIDERS:
        print(
            f"::error::{args.provider} offer listing is not implemented yet; "
            f"implemented providers: {', '.join(sorted(PROVIDERS))}"
        )
        return 1

    default_region = {
        "aliyun": "cn-hangzhou",
        "alibabacloud": "",
    }.get(args.provider, "us-east-1")
    provider = PROVIDERS[args.provider](region=args.region or default_region)
    try:
        offers = provider.list_offers()
    except MarketplaceError as error:
        print(f"::error::{error}")
        return 1

    markdown = render_markdown(provider, offers)
    summary = _summary_path(args.summary_file)
    if summary:
        summary.parent.mkdir(parents=True, exist_ok=True)
        with summary.open("a", encoding="utf-8") as file:
            file.write(markdown)
        print(f"Listed {len(offers)} {args.provider} offer(s). See the workflow summary.", file=sys.stderr)
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
