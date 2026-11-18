#!/usr/bin/env python3
"""
Industrial Lexicon & Cross-Border Supply Chain Knowledge Base
=============================================================
Translates Western viral e-commerce product names / URLs into:
1. Authentic 1688 factory-floor Chinese search queries (avoiding retail Taobao middleman terms)
2. GBK-encoded native 1688 manufacturer search URLs (1688 requires GBK query encoding!)
3. Manufacturing cluster mapping (Shenzhen, Dongguan, Yiwu, Ningbo, Zhongshan, Guangzhou, Shantou)
4. Cargo logistics classification (General vs Battery/Magnetic Sensitive vs Liquid/Cosmetic)
5. Realistic default benchmark specs (typical 1688 factory RMB cost, weight, retail anchor, QC checks)
"""

from dataclasses import dataclass
import re
import urllib.parse
from typing import List, Optional, Tuple


@dataclass
class ProductSupplyProfile:
    raw_input: str
    clean_title: str
    chinese_factory_query: str
    industrial_belt: str
    cargo_sensitivity: str  # GENERAL | BATTERY_MAGNETIC | LIQUID_COSMETIC | BULKY_VOLUMETRIC
    retail_price_usd: float
    weight_grams: int
    estimated_factory_cny: float
    moq_typical: int
    direct_1688_url: str
    viral_hooks: List[str]
    qc_checklist: List[str]


# Curated high-frequency cross-border e-commerce category archetypes
CATEGORY_RULES = [
    {
        "patterns": ["neck phone", "magnetic mount", "pov mount", "magsafe tripod", "phone holder", "car mount"],
        "cn_core": "磁吸挂脖手机支架 第一视角 源头工厂 私模",
        "belt": "Shenzhen / Dongguan (3C Magnetic & Silicone Mold Cluster)",
        "cargo": "BATTERY_MAGNETIC",
        "default_retail": 27.99,
        "default_weight_g": 260,
        "default_cny": 24.5,
        "moq": 50,
        "hooks": [
            "POV 0-3s Hook: Show both hands busy cooking/unboxing while camera glides smoothly at chest level — 'Stop holding your phone with your chin.'",
            "Durability Hook: Shake test N52 magnetic ring upside down over a pillow to crush fear of dropping an iPhone.",
        ],
        "qc": [
            "Pull-test N52 neodymium magnet array (>= 1.8kg vertical hold) and verify Magsafe metal ring alignment.",
            "Flex-test internal aluminum-magnesium alloy gooseneck 200 cycles at silicone seam.",
        ],
    },
    {
        "patterns": ["thermal printer", "pocket printer", "mini printer", "label maker", "sticker printer"],
        "cn_core": "迷你热敏口袋打印机 错题标签机 蓝牙跨境源头厂家",
        "belt": "Shenzhen / Zhuhai (Thermal Printhead & Consumer Electronics Cluster)",
        "cargo": "BATTERY_MAGNETIC",
        "default_retail": 24.99,
        "default_weight_g": 210,
        "default_cny": 36.0,
        "moq": 50,
        "hooks": [
            "Study/ADHD Organization Hook (0-3s): Rip a crisp black-and-white anatomy diagram or pantry label in 2 seconds with zero ink.",
            "Cost-Comparison Hook: ' Zero ink cartridges forever — 10 rolls of sticker paper cost less than one coffee.'",
        ],
        "qc": [
            "Verify English/multi-language companion App BLE pairing speed (<4s on iOS & Android) with no Mainland phone-number login wall!",
            "Check UN38.3 MSDS lithium battery report for smooth US/EU air-special-line customs clearance.",
        ],
    },
    {
        "patterns": ["gua sha", "facial massager", "red light", "led mask", "microcurrent", "beauty wand", "blackhead"],
        "cn_core": "电动刮痧板 彩光加热美容仪 外贸英文中性包装 源头工厂",
        "belt": "Shenzhen Bao'an / Guangzhou Baiyun (Personal Care & Beauty Device Cluster)",
        "cargo": "BATTERY_MAGNETIC",
        "default_retail": 34.99,
        "default_weight_g": 180,
        "default_cny": 29.0,
        "moq": 50,
        "hooks": [
            "Morning Puffiness Split-Screen Hook (0-3s): Massage only LEFT jawline for 60 seconds and show visible depuffing side-by-side.",
            "Spa-Savings Angle: '$34 once vs $140 lymphatic facial appointment — do it while watching Netflix.'",
        ],
        "qc": [
            "Ensure neutral English box + CE/FCC/RoHS markings; strictly avoid unsubstantiated medical claims on insert card (prevents TikTok Shop listing freeze).",
            "Test heating element cutoff thermostat (must cap at 42-45°C to prevent skin burn 1-star reviews).",
        ],
    },
    {
        "patterns": ["humidi", "diffuser", "flame", "aroma", "air purifier", "desk fan", "heater"],
        "cn_core": "火焰香薰机 加湿器 跨境专供 美规欧规 源头工厂",
        "belt": "Ningbo Cixi / Zhongshan / Shenzhen (Small Home Appliance Cluster)",
        "cargo": "GENERAL",
        "default_retail": 29.99,
        "default_weight_g": 380,
        "default_cny": 26.0,
        "moq": 60,
        "hooks": [
            "Dark-Room Ambience Hook (0-3s): Turn off bedroom lights and let realistic ultrasonic mist 'flames' glow instantly.",
            "ASMR Water-Pour Hook: Crisp water pour + 2 drops of essential oil + instant cozy desk vibe.",
        ],
        "qc": [
            "Check USB-C 5V power draw compatibility and verify auto shut-off sensor when water tank runs dry.",
            "Inspect box crush resistance (E-flute corrugated mailer) to survive direct cross-border packet transit.",
        ],
    },
    {
        "patterns": ["posture", "knee brace", "back stretcher", "massage pillow", "neck traction", "yoga", "pilates"],
        "cn_core": "矫姿带 护膝颈椎牵引 跨境爆款 源头工厂 现货",
        "belt": "Yangzhou / Hengshui / Yiwu (Orthotic Support & Fitness Textile Cluster)",
        "cargo": "GENERAL",
        "default_retail": 26.99,
        "default_weight_g": 230,
        "default_cny": 16.5,
        "moq": 100,
        "hooks": [
            "Desk-Slouch Callout Hook (0-3s): Catch a programmer slouching like a shrimp -> snap straps -> instant upright relief.",
            "Under-Shirt Invisible Test: Put a fitted t-shirt over it to prove zero bulky outline.",
        ],
        "qc": [
            "Audit US/EU sizing chart! Chinese domestic L = US S/M; mislabeled sizing causes 25%+ apparel/brace refund rates!",
            "Test Velcro hook-and-loop shear life and breathable neoprene odor after sealed polybag storage.",
        ],
    },
    {
        "patterns": ["pet", "cat", "dog", "grooming", "bark", "litter", "steam brush"],
        "cn_core": "宠物蒸汽刷 逗猫玩具 亚马逊TikTok跨境爆款 源头工厂",
        "belt": "Yiwu / Wenzhou Pingyang / Dongguan (Pet Supplies Cluster)",
        "cargo": "BATTERY_MAGNETIC",
        "default_retail": 22.99,
        "default_weight_g": 190,
        "default_cny": 15.8,
        "moq": 50,
        "hooks": [
            "Satisfying Fur-Peel Hook (0-3s): Peel a whole pancake of shed cat hair off the brush in one piece.",
            "Pet Reaction Hook: Show a grumpy cat purring and leaning into the warm mist brush.",
        ],
        "qc": [
            "Silicone bristle tip softness check + leak test on mist reservoir plug.",
            "Verify quiet motor decibel (<50dB) so timid pets don't bolt.",
        ],
    },
    {
        "patterns": ["serum", "cream", "patch", "lip", "sunscreen", "shampoo", "oil", "wax"],
        "cn_core": "外贸英文版 护肤贴 精华 跨境代发 实力源头工厂 FDA备案",
        "belt": "Guangzhou Baiyun / Shantou (Cosmetics & OEM Formulation Cluster)",
        "cargo": "LIQUID_COSMETIC",
        "default_retail": 19.99,
        "default_weight_g": 120,
        "default_cny": 8.5,
        "moq": 100,
        "hooks": [
            "Texture Macro Hook (0-3s): Close-up glass-skin absorption or overnight hydrocolloid gunk peel.",
            "Ingredient Transparency Hook: Compare active % directly against $68 Sephora incumbent.",
        ],
        "qc": [
            "MANDATORY: Verify US MoCRA / FDA cosmetic facility registration & English INCI ingredient list before listing on TikTok Shop US!",
            "Vacuum leak test bottle cap under low air pressure (air-freight cabin depressurization leaks ruin batches).",
        ],
    },
]

# Word-level industrial fallback dictionary for arbitrary English queries
TOKEN_CN_MAP = {
    "wireless": "无线",
    "portable": "便携迷你",
    "magnetic": "强磁吸",
    "foldable": "折叠",
    "waterproof": "防水",
    "rechargeable": "充电款",
    "electric": "电动",
    "silicone": "食品级硅胶",
    "stainless": "304不锈钢",
    "led": "LED发光",
    "lamp": "氛围灯",
    "light": "感应灯",
    "organizer": "收纳盒",
    "kitchen": "厨房小工具",
    "chopper": "切菜器",
    "blender": "榨汁杯",
    "car": "车载",
    "vacuum": "吸尘器",
    "bag": "收纳包",
    "backpack": "双肩包",
    "jewelry": "饰品钛钢",
    "sunglasses": "偏光太阳镜",
    "toy": "益智玩具",
    "desk": "桌面办公",
    "stand": "支架",
    "cleaner": "清洁刷",
}


def build_1688_gbk_search_url(chinese_query: str) -> str:
    """
    1688's selloffer search endpoint natively expects GBK percent-encoded bytes!
    Encoding in GBK avoids mojibake and opens directly into wholesale factory offers.
    """
    try:
        encoded = urllib.parse.quote(chinese_query.encode("gbk", errors="ignore"))
    except LookupError:
        encoded = urllib.parse.quote(chinese_query.encode("utf-8"))
    return f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded}&filt=y"


def parse_pipe_or_url_input(raw_line: str) -> Tuple[str, Optional[float], Optional[int], Optional[float]]:
    """
    Supports flexible seller inputs:
    - "Magnetic Neck Phone Holder | 27.99 | 260g | 24.5"
    - "https://www.amazon.com/Portable-Thermal-Pocket-Printer/dp/B09XXXX"
    - "Electric Gua Sha Facial Massager"
    Returns: (clean_title, retail_usd_override, weight_g_override, cny_cost_override)
    """
    parts = [p.strip() for p in raw_line.split("|")]
    head = parts[0]

    # Extract slug if input is a URL
    if head.startswith("http://") or head.startswith("https://"):
        parsed = urllib.parse.urlparse(head)
        path_tokens = [seg for seg in parsed.path.split("/") if seg and not seg.startswith("B0") and seg != "dp"]
        slug = " ".join(path_tokens[:2]) if path_tokens else parsed.netloc
        clean_title = re.sub(r"[-_+.]+", " ", slug).strip()
        if not clean_title:
            clean_title = head
    else:
        clean_title = head

    retail_override: Optional[float] = None
    weight_override: Optional[int] = None
    cny_override: Optional[float] = None

    for extra in parts[1:]:
        low = extra.lower().strip()
        if low.endswith("g") and not low.endswith("kg"):
            num = re.sub(r"[^0-9.]", "", low)
            if num:
                weight_override = int(float(num))
        elif low.endswith("kg"):
            num = re.sub(r"[^0-9.]", "", low)
            if num:
                weight_override = int(float(num) * 1000)
        elif low.startswith("¥") or low.endswith("cny") or low.endswith("rmb"):
            num = re.sub(r"[^0-9.]", "", low)
            if num:
                cny_override = float(num)
        else:
            num = re.sub(r"[^0-9.]", "", low)
            if num:
                val = float(num)
                if retail_override is None:
                    retail_override = val
                elif cny_override is None:
                    cny_override = val

    return clean_title, retail_override, weight_override, cny_override


def build_supply_profile(raw_input: str) -> ProductSupplyProfile:
    clean_title, retail_ov, weight_ov, cny_ov = parse_pipe_or_url_input(raw_input)
    lower_title = clean_title.lower()

    matched_rule = None
    for rule in CATEGORY_RULES:
        if any(pat in lower_title for pat in rule["patterns"]):
            matched_rule = rule
            break

    if matched_rule:
        cn_query = matched_rule["cn_core"]
        belt = matched_rule["belt"]
        cargo = matched_rule["cargo"]
        retail = retail_ov if retail_ov is not None else matched_rule["default_retail"]
        weight_g = weight_ov if weight_ov is not None else matched_rule["default_weight_g"]
        cny = cny_ov if cny_ov is not None else matched_rule["default_cny"]
        moq = matched_rule["moq"]
        hooks = list(matched_rule["hooks"])
        qc = list(matched_rule["qc"])
    else:
        # Dynamic token synthesis for arbitrary long-tail products
        words = re.findall(r"[a-z0-9]+", lower_title)
        cn_tokens = [TOKEN_CN_MAP[w] for w in words if w in TOKEN_CN_MAP]
        if not cn_tokens:
            cn_tokens = [clean_title[:30]]
        cn_query = " ".join(cn_tokens) + " 跨境专供 源头工厂 现货"

        if any(k in lower_title for k in ["electric", "wireless", "usb", "led", "battery", "magnetic", "smart"]):
            cargo = "BATTERY_MAGNETIC"
            belt = "Shenzhen / Dongguan / Ningbo (Electronics & Mold Cluster)"
        elif any(k in lower_title for k in ["liquid", "gel", "spray", "lotion", "perfume"]):
            cargo = "LIQUID_COSMETIC"
            belt = "Guangzhou / Shantou (Daily Chemical OEM Cluster)"
        else:
            cargo = "GENERAL"
            belt = "Yiwu / Taizhou / Jieyang (General Consumer Goods & Hardware Cluster)"

        retail = retail_ov if retail_ov is not None else 26.99
        weight_g = weight_ov if weight_ov is not None else 250
        # Realistic heuristic: primary 1688 factory Ex-Works is typically ~11%–14% of Western DTC retail
        cny = cny_ov if cny_ov is not None else round(retail * 0.125 * 7.22, 1)
        moq = 50
        hooks = [
            f"Problem-Agitation Hook (0-3s): Show the exact frustrating daily fail without '{clean_title}' before revealing the 2-second fix.",
            "Side-by-Side Torture Test: Pit your unit directly against the overpriced $55 retail store version.",
        ]
        qc = [
            "Request unedited factory floor video + sample drop test on shipping carton before paying 70% balance.",
            "Verify neutral English packaging with barcode label space and zero Chinese retail price tags.",
        ]

    return ProductSupplyProfile(
        raw_input=raw_input,
        clean_title=clean_title,
        chinese_factory_query=cn_query,
        industrial_belt=belt,
        cargo_sensitivity=cargo,
        retail_price_usd=round(retail, 2),
        weight_grams=max(weight_g, 20),
        estimated_factory_cny=round(cny, 2),
        moq_typical=moq,
        direct_1688_url=build_1688_gbk_search_url(cn_query),
        viral_hooks=hooks,
        qc_checklist=qc,
    )
