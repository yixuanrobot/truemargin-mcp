#!/usr/bin/env python3
"""
TrueMargin MCP Server (Model Context Protocol — JSON-RPC 2.0 over stdio)
========================================================================
Zero-dependency MCP server allowing Claude Desktop, Cursor, Windsurf, Cline, and n8n
AI Agents to audit 1688 primary factory sourcing & TikTok Shop / Amazon FBA net margins.

Interactive Web App & Bulk CSV Pro Suite: https://truemargin.aitruelabs.com
Apify Cloud Actor: https://apify.com/aitruelabs/truemargin-1688-profit-scout
"""

import json
import sys
from typing import Any, Dict, List

from .industrial_lexicon import build_supply_profile
from .margin_engine import compute_unit_economics
from .sourcing_scraper import match_verified_factories, try_fetch_page_title_and_price


def _safe_float(val: Any, default: float) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def audit_batch(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = args.get("items") or []
    sales_channel = str(args.get("salesChannel") or "tiktok_shop_us")
    shipping_mode = str(args.get("shippingMode") or "direct_packet_3pl")
    affiliate_pct = _safe_float(args.get("creatorAffiliatePct"), 15.0)
    refund_pct = _safe_float(args.get("expectedRefundRatePct"), 14.0)
    cpa_usd = _safe_float(args.get("adSpendCpaUsd"), 3.50)
    min_repurchase = _safe_float(args.get("minFactoryRepurchaseRatePct"), 20.0)
    fx_rate = _safe_float(args.get("usdCnyRate"), 7.22)

    records: List[Dict[str, Any]] = []
    for raw_item in items:
        raw_str = str(raw_item).strip() if not isinstance(raw_item, dict) else str(
            raw_item.get("query") or raw_item.get("title") or raw_item.get("url") or ""
        ).strip()
        if not raw_str:
            continue

        enriched = raw_str
        if enriched.startswith("http://") or enriched.startswith("https://"):
            meta = try_fetch_page_title_and_price(enriched)
            if meta and meta.get("title"):
                enriched = f"{meta['title']} | {meta['price']}" if meta.get("price") else meta["title"]

        profile = build_supply_profile(enriched)
        factories = match_verified_factories(profile, min_repurchase_rate_pct=min_repurchase)
        best_cny = factories[0].unitPriceCny if factories else profile.estimated_factory_cny
        econ = compute_unit_economics(
            retail_price_usd=profile.retail_price_usd,
            factory_unit_cny=best_cny,
            weight_grams=profile.weight_grams,
            cargo_sensitivity=profile.cargo_sensitivity,
            sales_channel=sales_channel,
            shipping_mode=shipping_mode,
            creator_affiliate_pct=affiliate_pct,
            expected_refund_rate_pct=refund_pct,
            ad_spend_cpa_usd=cpa_usd,
            usd_cny_rate=fx_rate,
        )

        records.append({
            "productQuery": raw_str,
            "verdict": econ.verdict,
            "chineseFactoryQuery": profile.chinese_factory_query,
            "industrialBelt": profile.industrial_belt,
            "cargoSensitivity": profile.cargo_sensitivity,
            "direct1688SearchUrl": profile.direct_1688_url,
            "retailPriceUsd": econ.retail_price_usd,
            "estimatedFactoryCostCny": econ.factory_unit_cny,
            "landedCogsUsd": econ.landed_cogs_usd,
            "netProfitPerOrderUsd": econ.net_profit_usd,
            "netMarginPct": econ.net_margin_pct,
            "breakEvenRoas": econ.break_even_roas,
            "merchantPrescription": econ.merchant_prescription,
            "marginWaterfall": econ.to_dict(),
            "verifiedFactories": [f.to_dict() for f in factories],
            "webDashboardUrl": "https://truemargin.aitruelabs.com",
        })
    return records


TOOLS_SPEC = [
    {
        "name": "audit_crossborder_sku_margin",
        "description": (
            "Audits one or more e-commerce product titles or URLs for 1688 primary factory RMB cost, "
            "GBK-encoded 1688 search URLs, battery/magnetic/liquid sensitive-cargo DDP shipping surcharges, "
            "TikTok Shop / Shopify / Amazon FBA fees, refund RTO bleed, and returns a GO / CAUTION / KILL verdict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of English product names, URLs, or 'Title | RetailUSD | WeightGrams | OptionalFactoryCNY' strings.",
                },
                "salesChannel": {
                    "type": "string",
                    "enum": ["tiktok_shop_us", "shopify_dtc", "amazon_fba_us"],
                    "default": "tiktok_shop_us",
                },
                "shippingMode": {
                    "type": "string",
                    "enum": ["direct_packet_3pl", "air_ddp_fast", "sea_ddp_bulk"],
                    "default": "direct_packet_3pl",
                },
                "creatorAffiliatePct": {"type": "number", "default": 15.0},
                "expectedRefundRatePct": {"type": "number", "default": 14.0},
                "adSpendCpaUsd": {"type": "number", "default": 3.50},
            },
            "required": ["items"],
        },
    },
    {
        "name": "translate_1688_factory_query",
        "description": (
            "Converts an English product name into industrial-belt Chinese 1688 source-factory search terms, "
            "manufacturing cluster location, cargo sensitivity class, and a GBK-encoded direct 1688 search URL."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "productTitle": {
                    "type": "string",
                    "description": "English product name (e.g. 'Magnetic POV Neck Phone Holder').",
                }
            },
            "required": ["productTitle"],
        },
    },
]


def handle_rpc_request(req: Dict[str, Any]) -> Dict[str, Any]:
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        client_proto = ((req.get("params") or {}).get("protocolVersion")) or "2024-11-05"
        supported = client_proto if client_proto in ("2024-11-05", "2025-03-26") else "2024-11-05"
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": supported,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "truemargin-1688-scout", "version": "1.0.0"},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_SPEC}}

    if method == "tools/call":
        params = req.get("params") or {}
        tool_name = params.get("name")
        args = params.get("arguments") or {}

        if tool_name == "audit_crossborder_sku_margin":
            records = audit_batch(args)
            payload = {
                "auditedCount": len(records),
                "interactiveBulkWebApp": "https://truemargin.aitruelabs.com",
                "audits": records,
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]},
            }

        if tool_name == "translate_1688_factory_query":
            title = str(args.get("productTitle") or "").strip()
            profile = build_supply_profile(title or "Cross-Border Gadget")
            payload = {
                "englishInput": title,
                "chineseFactoryQuery": profile.chinese_factory_query,
                "industrialBelt": profile.industrial_belt,
                "cargoSensitivity": profile.cargo_sensitivity,
                "direct1688GbkSearchUrl": profile.direct_1688_url,
                "qcChecklist": profile.qc_checklist,
                "interactiveCalculator": "https://truemargin.aitruelabs.com",
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
        }

    if req_id is None:
        return {}
    return {"jsonrpc": "2.0", "id": req_id, "result": {}}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_rpc_request(req)
        if resp:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
