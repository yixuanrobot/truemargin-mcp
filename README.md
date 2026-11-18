# ⚖️ TrueMargin MCP Server (`truemargin-mcp`)

**Zero-dependency Model Context Protocol (MCP) server for cross-border e-commerce unit economics & 1688 primary factory sourcing.**

Give **Claude Desktop**, **Cursor**, **Windsurf**, **Cline**, and **n8n AI Agents** instant access to real landed-COGS calculations, GBK-encoded 1688 factory search links, sensitive-cargo air/sea DDP freight surcharges, and **TikTok Shop / Amazon FBA / Shopify DTC** net contribution margins.

> 🌐 **No-Login Interactive Web Calculator & 200-SKU Bulk CSV Pro Suite**: **[https://truemargin.aitruelabs.com](https://truemargin.aitruelabs.com)**
> 🕷️ **Cloud Batch API on Apify Store**: **[aitruelabs/truemargin-1688-profit-scout](https://apify.com/aitruelabs/truemargin-1688-profit-scout)**

---

## Why Sellers & Sourcing Agents Need This

1. **Escape the 1688 Middleman Trap**: Literal Google Translate queries on 1688.com route foreign buyers to Yiwu/Taobao trading companies (`商行` / `电子商务`, +30–40% markup) instead of Shenzhen/Dongguan/Ningbo primary plants (`源头工厂` / `实业`). Plus, 1688's native search endpoint requires **GBK-encoded** byte URLs.
2. **Expose the "TikTok Shop GMV Illusion"**: Buying an item for ¥20 ($2.80) and selling it for $24.99 looks profitable—until battery/magnetic sensitive-line freight (+30%), 6.5% tariff buffer, 6% platform referral, 15% creator affiliate cut, and 14% impulse refund RTO bleed wipe out your margin.
3. **100% Pure Python Stdlib**: Zero third-party packages required (`dependencies = []`). Starts in `<100ms` via `uvx` or `python3`.

---

## Quick Start (Claude Desktop / Cursor / Windsurf)

### Option A: Zero-Install via `uvx` (Recommended)

Add this to your `claude_desktop_config.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "truemargin-1688-scout": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/yixuanrobot/truemargin-mcp",
        "truemargin-mcp"
      ]
    }
  }
}
```

### Option B: Clone & Run Directly with `python3`

```bash
git clone https://github.com/yixuanrobot/truemargin-mcp.git
```

```json
{
  "mcpServers": {
    "truemargin-1688-scout": {
      "command": "python3",
      "args": ["-m", "truemargin_mcp"],
      "cwd": "/path/to/truemargin-mcp"
    }
  }
}
```

---

## Exposed MCP Tools

### 1. `audit_crossborder_sku_margin`
Audits one or more SKUs (`Title | RetailUSD | WeightGrams | OptionalFactoryCNY` or product URLs) across `tiktok_shop_us`, `amazon_fba_us`, or `shopify_dtc`.

**Example Prompt in Claude / Cursor:**
> *"Use TrueMargin to audit `Magnetic POV Neck Phone Holder | 27.99 | 260g` and `Cheap Pet Hair Roller | 12.99 | 240g` on TikTok Shop US with 15% affiliate commission and air packet shipping. Tell me which one to kill."*

**Returned Structured Fields:**
- `verdict`: `GO` / `CAUTION` / `KILL`
- `chineseFactoryQuery` & `direct1688SearchUrl` (GBK-encoded)
- `industrialBelt` (e.g., *Shenzhen / Dongguan 3C Magnetic & Silicone Mold Cluster*)
- `cargoSensitivity`: `GENERAL` | `BATTERY_MAGNETIC` | `LIQUID_COSMETIC` | `BULKY_VOLUMETRIC`
- `marginWaterfall`: Full line-by-line USD breakdown + `breakEvenRoas`
- `verifiedFactories`: Primary manufacturer benchmarks filtered by B2B repurchase rate (`回头率`)

### 2. `translate_1688_factory_query`
Instantly maps an English SKU title into native industrial-cluster Mandarin factory keywords, QC inspection gates, and a clickable GBK-encoded 1688 search link.

---

## Need Bulk CSV Exports, Visual Waterfalls, or Team Access?

- **Interactive Web App & Pro Bulk CSV Suite**: [https://truemargin.aitruelabs.com](https://truemargin.aitruelabs.com)
- **Hosted Cloud Actor (Webhook / n8n / Make)**: [https://apify.com/aitruelabs/truemargin-1688-profit-scout](https://apify.com/aitruelabs/truemargin-1688-profit-scout)

---

## License

MIT © [AI True Labs](https://aitruelabs.com) (`support@aitruelabs.com`)
