from __future__ import annotations

import json
import os


def fetch_aliyun_product(code: str, timeout: float = 30) -> dict[str, object]:
    """Fetch one public product's name and short description from Aliyun Market."""
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip()
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "").strip()
    security_token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN", "").strip()
    if not access_key_id or not access_key_secret:
        raise RuntimeError(
            "set ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET "
            "(and ALIBABA_CLOUD_SECURITY_TOKEN when using STS credentials)"
        )

    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkmarket.request.v20151101.DescribeProductRequest import DescribeProductRequest
    except ImportError as error:
        raise RuntimeError("install the Aliyun SDK with: pip install '.[aliyun]'") from error

    credential = None
    if security_token:
        try:
            from aliyunsdkcore.auth.credentials import StsTokenCredential
        except ImportError as error:
            raise RuntimeError("installed Aliyun SDK does not support STS credentials") from error
        credential = StsTokenCredential(
            sts_access_key_id=access_key_id,
            sts_access_key_secret=access_key_secret,
            sts_token=security_token,
        )

    if credential is None:
        client = AcsClient(access_key_id, access_key_secret, "cn-hangzhou", timeout=timeout)
    else:
        client = AcsClient(region_id="cn-hangzhou", credential=credential, timeout=timeout)

    request = DescribeProductRequest()
    request.set_Code(code)
    request.set_QueryDraft(False)
    try:
        response = client.do_action_with_exception(request)
    except Exception as error:
        # SDK exceptions can contain signed request details; only surface the
        # exception class to avoid accidentally printing credentials or tokens.
        raise RuntimeError(f"Aliyun Market API request failed ({type(error).__name__})") from None
    parsed = json.loads(response.decode("utf-8") if isinstance(response, bytes) else response)
    result = parsed.get("Result", parsed)
    if not isinstance(result, dict):
        raise RuntimeError("Aliyun returned an unexpected product response")
    return result
