#!/usr/bin/env python3
"""
True Contribution-Margin Financial Engine
==========================================
Exposes the "GMV Illusion" across TikTok Shop US, Shopify DTC, and Amazon FBA US
by modeling landed factory COGS, sensitive-cargo surcharges, affiliate cuts, and RTO losses.
"""

from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class MarginBreakdown:
    sales_channel: str
    shipping_mode: str
    cargo_sensitivity: str
    retail_price_usd: float
    factory_unit_cny: float
    factory_unit_usd: float
    china_inland_and_qc_usd: float
    intl_freight_and_tariff_usd: float
    landed_cogs_usd: float
    platform_referral_fee_usd: float
    creator_affiliate_fee_usd: float
    fba_or_lastmile_fee_usd: float
    refund_rto_loss_usd: float
    ad_and_sample_cpa_usd: float
    net_profit_usd: float
    net_margin_pct: float
    break_even_roas: float
    verdict: str
    merchant_prescription: str

    def to_dict(self) -> Dict:
        return asdict(self)


# Per-kg CNY rates + parcel registration fee CNY by mode and cargo sensitivity
LOGISTICS_RATES_CNY = {
    "direct_packet_3pl": {
        "GENERAL": {"per_kg": 68.0, "reg_fee": 15.0, "last_mile_usd": 0.0},
        "BATTERY_MAGNETIC": {"per_kg": 88.0, "reg_fee": 18.0, "last_mile_usd": 0.0},
        "LIQUID_COSMETIC": {"per_kg": 96.0, "reg_fee": 20.0, "last_mile_usd": 0.0},
    },
    "air_ddp_fast": {
        "GENERAL": {"per_kg": 42.0, "reg_fee": 0.0, "last_mile_usd": 4.20},
        "BATTERY_MAGNETIC": {"per_kg": 54.0, "reg_fee": 0.0, "last_mile_usd": 4.20},
        "LIQUID_COSMETIC": {"per_kg": 62.0, "reg_fee": 0.0, "last_mile_usd": 4.20},
    },
    "sea_ddp_bulk": {
        "GENERAL": {"per_kg": 13.5, "reg_fee": 0.0, "last_mile_usd": 4.20},
        "BATTERY_MAGNETIC": {"per_kg": 18.5, "reg_fee": 0.0, "last_mile_usd": 4.20},
        "LIQUID_COSMETIC": {"per_kg": 22.0, "reg_fee": 0.0, "last_mile_usd": 4.20},
    },
}


def compute_unit_economics(
    retail_price_usd: float,
    factory_unit_cny: float,
    weight_grams: int,
    cargo_sensitivity: str = "GENERAL",
    sales_channel: str = "tiktok_shop_us",
    shipping_mode: str = "direct_packet_3pl",
    creator_affiliate_pct: float = 15.0,
    expected_refund_rate_pct: float = 14.0,
    ad_spend_cpa_usd: float = 3.50,
    usd_cny_rate: float = 7.22,
) -> MarginBreakdown:
    fx = max(usd_cny_rate, 6.0)
    weight_kg = max(weight_grams, 20) / 1000.0
    # Add 15% packaging corrugated box weight buffer
    billed_kg = weight_kg * 1.15

    mode_table = LOGISTICS_RATES_CNY.get(shipping_mode, LOGISTICS_RATES_CNY["direct_packet_3pl"])
    rate_cfg = mode_table.get(cargo_sensitivity, mode_table["GENERAL"])

    factory_usd = factory_unit_cny / fx
    # China domestic freight from 1688 factory to Shenzhen/Yiwu 3PL (~¥2.2) + QC & barcode label ($0.35)
    china_inland_qc_usd = (2.20 / fx) + 0.35

    freight_cny = billed_kg * rate_cfg["per_kg"] + rate_cfg["reg_fee"]
    # Include 6.5% landed customs duty/clearance buffer on declared wholesale value
    tariff_buffer_usd = factory_usd * 0.065
    intl_freight_usd = (freight_cny / fx) + tariff_buffer_usd

    landed_cogs_usd = factory_usd + china_inland_qc_usd + intl_freight_usd

    r = max(0.0, min(1.0, expected_refund_rate_pct / 100.0))

    last_mile_usd = rate_cfg["last_mile_usd"]
    affiliate_usd = 0.0

    if sales_channel == "tiktok_shop_us":
        # TikTok Shop US ~6% referral fee + creator affiliate %
        platform_fee_usd = retail_price_usd * 0.06
        affiliate_usd = retail_price_usd * (creator_affiliate_pct / 100.0)
        # Refunded order: $0 revenue kept, creator affiliate clawed back ($0),
        # TikTok retains ~20% refund admin fee (capped at $5.00), ~75% landed COGS + last-mile unrecovered
        refund_admin_fee = min(platform_fee_usd * 0.20, 5.00)
        unrecoverable_cogs_and_ship = landed_cogs_usd * 0.75 + last_mile_usd
    elif sales_channel == "amazon_fba_us":
        platform_fee_usd = retail_price_usd * 0.15
        # Override last-mile with FBA Pick & Pack fee tiered by weight
        if billed_kg <= 0.25:
            last_mile_usd = 3.86
        elif billed_kg <= 0.50:
            last_mile_usd = 4.55
        else:
            last_mile_usd = 5.65 + max(0.0, billed_kg - 0.50) * 1.60
        # Amazon FBA doesn't use TikTok creator affiliate by default unless external traffic
        affiliate_usd = retail_price_usd * (creator_affiliate_pct / 100.0) * 0.25
        refund_admin_fee = min(platform_fee_usd * 0.20, 5.00)
        unrecoverable_cogs_and_ship = landed_cogs_usd * 0.55 + last_mile_usd
    else:
        # Shopify DTC: ~3.9% MoR / Card blended + $0.40 fixed (gateway fee is NOT refunded on returns)
        platform_fee_usd = retail_price_usd * 0.039 + 0.40
        affiliate_usd = retail_price_usd * (creator_affiliate_pct / 100.0) * 0.30
        refund_admin_fee = platform_fee_usd
        unrecoverable_cogs_and_ship = landed_cogs_usd * 0.70 + last_mile_usd

    kept_contribution = (
        retail_price_usd
        - landed_cogs_usd
        - last_mile_usd
        - platform_fee_usd
        - affiliate_usd
    )
    loss_on_refunded_order = unrecoverable_cogs_and_ship + refund_admin_fee

    gross_before_ads = (1.0 - r) * kept_contribution - r * loss_on_refunded_order
    effective_refund_impact = r * (kept_contribution + loss_on_refunded_order)
    net_profit = gross_before_ads - ad_spend_cpa_usd
    net_margin_pct = (net_profit / retail_price_usd * 100.0) if retail_price_usd > 0 else -100.0

    # Break-Even Ad ROAS = Retail Price / Max Affordable CPA (gross_before_ads)
    if gross_before_ads > 0.25:
        break_even_roas = round(retail_price_usd / gross_before_ads, 2)
    else:
        break_even_roas = 99.99  # Impossible to run profitable ads at current price

    if net_margin_pct >= 22.0 and net_profit >= 5.50:
        verdict = "GO"
        prescription = (
            f"Healthy unit economics (${net_profit:.2f}/order, {net_margin_pct:.1f}% net). "
            f"Keep paid ad ROAS above {break_even_roas}x and lock MOQ discount after first 100 orders."
        )
    elif net_margin_pct >= 10.0 and net_profit >= 2.50:
        target_price = round(retail_price_usd + 6.0, 2)
        verdict = "CAUTION"
        prescription = (
            f"Thin safety cushion (${net_profit:.2f}/order). One viral refund spike will wipe profits. "
            f"FIX: Bundle into a 2-pack or gift-kit at ${target_price} OR switch shipping to Sea DDP once validated."
        )
    else:
        bundle_price = round(max(retail_price_usd * 1.65, landed_cogs_usd * 4.2), 2)
        verdict = "KILL"
        prescription = (
            f"GMV ILLUSION TRAP (${net_profit:.2f}/order)! You lose/barely break even after {creator_affiliate_pct:.0f}% affiliate "
            f"& {expected_refund_rate_pct:.0f}% returns. DO NOT launch single unit at ${retail_price_usd:.2f}; "
            f"either sell a 2-unit bundle at ${bundle_price} or kill this SKU immediately."
        )

    return MarginBreakdown(
        sales_channel=sales_channel,
        shipping_mode=shipping_mode,
        cargo_sensitivity=cargo_sensitivity,
        retail_price_usd=round(retail_price_usd, 2),
        factory_unit_cny=round(factory_unit_cny, 2),
        factory_unit_usd=round(factory_usd, 2),
        china_inland_and_qc_usd=round(china_inland_qc_usd, 2),
        intl_freight_and_tariff_usd=round(intl_freight_usd, 2),
        landed_cogs_usd=round(landed_cogs_usd, 2),
        platform_referral_fee_usd=round(platform_fee_usd, 2),
        creator_affiliate_fee_usd=round(affiliate_usd, 2),
        fba_or_lastmile_fee_usd=round(last_mile_usd, 2),
        refund_rto_loss_usd=round(effective_refund_impact, 2),
        ad_and_sample_cpa_usd=round(ad_spend_cpa_usd, 2),
        net_profit_usd=round(net_profit, 2),
        net_margin_pct=round(net_margin_pct, 2),
        break_even_roas=break_even_roas,
        verdict=verdict,
        merchant_prescription=prescription,
    )
