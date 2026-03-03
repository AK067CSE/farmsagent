"""
Farming Expert Agent - Fixed Multi-Tool Version
Uses AgentTool to wrap single-tool sub-agents (bypasses multi-tool limit)
Supports: City | State | Pincode
Uses: OpenWeatherMap + Google Search
"""

import os
import asyncio
import requests
import json
import re
import time
from urllib.parse import urlparse
from typing import Dict, Any
from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import google_search, AgentTool, FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import ToolContext
from google.genai import types as genai_types

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

from prompts import (
    WEATHER_AGENT_INSTR,
    SEARCH_AGENT_INSTR,
    DHANUKA_IMAGE_AGENT_INSTR,
    FARMING_AGENT_INSTR,
    DHANUKA_KNOWLEDGE,
    get_dhanuka_recommendations,
    format_dhanuka_recommendation,
    # Also import searcher instructions from sub-agents
    FINANCE_SEARCHER_INSTR,
    POST_HARVEST_SEARCHER_INSTR,
    COMPLIANCE_SAFETY_SEARCHER_INSTR,
    MACHINERY_MECHANIZATION_SEARCHER_INSTR,
    SUSTAINABILITY_REGEN_SEARCHER_INSTR,
    SOIL_ANALYZER_SEARCHER_INSTR,
    MARKETING_SEARCHER_INSTR,
    CROP_DOCTOR_SEARCHER_INSTR,
    PLANT_GROWTH_SEARCHER_INSTR,
    CROP_PLANNER_INSTR,
    CROP_SEARCHER_INSTR,
    CROP_ADVISOR_INSTR,
    CROP_COORDINATOR_INSTR,
)

from prompts import (
    DHANUKA_CATALOG_TOOLING_RULES,
    DHANUKA_TEXT_ONLY_ADVISOR_INSTR,
    DHANUKA_IMAGE_ADVISOR_INSTR,
)

# =============================================================================
# Dhanuka Knowledge Integration
# =============================================================================

def _sync_knowledge_urls() -> None:
    return

# Load .env (local + global)
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"), override=True)
load_dotenv(override=True)

# Normalize Gemini key env var for ADK/google-genai
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "") or os.getenv("GENAI_API_KEY", "")

# =============================================================================
# LOCATION AND TIMEZONE UTILITIES
# =============================================================================

def get_location_datetime(location: str) -> Dict[str, Any]:
    """
    Get current date, time, month, season for any Indian location.
    
    Args:
        location (str): City name, state, or 6-digit Indian pincode
        
    Returns:
        Dict with datetime info, timezone, season, etc.
    """
    try:
        # Initialize geocoder and timezone finder
        geolocator = Nominatim(user_agent="farming_agent")
        tf = TimezoneFinder()
        
        # Get coordinates for location
        if location.isdigit() and len(location) == 6:
            # Handle Indian pincode
            location_query = f"{location}, India"
        else:
            location_query = f"{location}, India"
        
        location_data = geolocator.geocode(location_query)
        if not location_data:
            return {
                'error': 'Location not found',
                'location': location,
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timezone': 'Asia/Kolkata (IST)',
                'season': 'Unknown'
            }
        
        lat, lon = location_data.latitude, location_data.longitude
        
        # Get timezone
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        if not timezone_str:
            timezone_str = 'Asia/Kolkata'  # Default to IST
        
        # Get current time in that timezone
        tz = pytz.timezone(timezone_str)
        current_time = datetime.now(tz)
        
        # Determine Indian farming season
        month = current_time.month
        if month in [6, 7, 8, 9]:
            season = 'Kharif (Monsoon)'
        elif month in [10, 11, 12, 1, 2, 3]:
            season = 'Rabi (Winter)'
        elif month in [4, 5]:
            season = 'Zaid (Summer)'
        else:
            season = 'Unknown'
        
        return {
            'location': location_data.address if hasattr(location_data, 'address') else location,
            'coordinates': {'lat': lat, 'lon': lon},
            'timezone': timezone_str,
            'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'date': current_time.strftime('%Y-%m-%d'),
            'time': current_time.strftime('%H:%M:%S'),
            'month': current_time.strftime('%B'),
            'day': current_time.day,
            'year': current_time.year,
            'season': season,
            'is_weekend': current_time.weekday() >= 5,
            'month_number': month
        }
        
    except Exception as e:
        return {
            'error': f'Could not get location data: {str(e)}',
            'location': location,
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': 'Asia/Kolkata (IST)',
            'season': 'Unknown'
        }

# =============================================================================
# TOOL 1: WEATHER TOOL (NO LAT/LON)
# =============================================================================

def get_weather(location: str, tool_context: ToolContext) -> str:
    """
    Get current weather data for any Indian location.
    
    Args:
        location (str): City name, state, or 6-digit Indian pincode
        tool_context (ToolContext): ADK tool context for state management
        
    Returns:
        str: Comprehensive weather report or error message
    """
    api_key = os.environ.get("OPENWEATHER_API_KEY", "")
    if not api_key:
        return "Weather error: OPENWEATHER_API_KEY not configured."

    location = location.strip()

    try:
        if location.isdigit() and len(location) == 6:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather?"
                f"zip={location},IN&appid={api_key}&units=metric"
            )
        else:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather?"
                f"q={location},IN&appid={api_key}&units=metric"
            )

        response = requests.get(url, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return f"Weather error: {data.get('message', 'Location not found')}"

        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        sys = data.get("sys", {})
        coord = data.get("coord", {})
        rain = data.get("rain", {})
        snow = data.get("snow", {})

        # Format weather data with all available fields
        weather_report = (
            f"Weather Summary:\n"
            f"- Location: {data.get('name')}, {sys.get('country', 'N/A')}\n"
            f"- Coordinates: {coord.get('lat', 'N/A')}, {coord.get('lon', 'N/A')}\n"
            f"- Temperature: {main.get('temp', 'N/A')}°C (feels like: {main.get('feels_like', 'N/A')}°C)\n"
            f"- Min/Max: {main.get('temp_min', 'N/A')}°C / {main.get('temp_max', 'N/A')}°C\n"
            f"- Condition: {weather.get('main', 'N/A')} - {weather.get('description', 'N/A')}\n"
            f"- Humidity: {main.get('humidity', 'N/A')}%\n"
            f"- Pressure: {main.get('pressure', 'N/A')} hPa\n"
            f"- Sea Level Pressure: {main.get('sea_level', 'N/A')} hPa\n"
            f"- Ground Level Pressure: {main.get('grnd_level', 'N/A')} hPa\n"
            f"- Visibility: {data.get('visibility', 'N/A')} meters\n"
            f"- Wind Speed: {wind.get('speed', 'N/A')} m/s\n"
            f"- Wind Direction: {wind.get('deg', 'N/A')}°\n"
            f"- Wind Gust: {wind.get('gust', 'N/A')} m/s\n"
            f"- Cloudiness: {clouds.get('all', 'N/A')}%\n"
        )

        # Add rain data if available
        if rain:
            weather_report += f"- Rain (1h): {rain.get('1h', 'N/A')} mm\n"
        
        # Add snow data if available
        if snow:
            weather_report += f"- Snow (1h): {snow.get('1h', 'N/A')} mm\n"

        weather_report += (
            f"- Sunrise: {sys.get('sunrise', 'N/A')}\n"
            f"- Sunset: {sys.get('sunset', 'N/A')}\n"
            f"- Timezone: {data.get('timezone', 'N/A')} seconds from UTC\n"
            f"- Data Time: {data.get('dt', 'N/A')}\n"
        )

        # Store weather query in state for tracking
        tool_context.state["temp:last_weather_query"] = location
        tool_context.state["temp:last_weather_result"] = weather_report
        
        # Update temporal context for the location
        temporal_data = get_location_datetime(location)
        tool_context.state["current_date"] = temporal_data.get("date", "")
        tool_context.state["current_time"] = temporal_data.get("time", "")
        tool_context.state["current_month"] = temporal_data.get("month", "")
        tool_context.state["current_season"] = temporal_data.get("season", "")
        tool_context.state["timezone"] = temporal_data.get("timezone", "")
        tool_context.state["current_location"] = location
        
        return weather_report

    except Exception as e:
        return f"Weather error: {str(e)}"

# =============================================================================
# DHANUKA SCRAPED CATALOG (Context Engineering Tools)
# =============================================================================

_DHANUKA_URLS_PATH = os.path.join(_HERE, "complete_dhanuka_urls.json")
_DHANUKA_CACHE_PATH = os.path.join(_HERE, "dhanuka_products_cache.json")


def _read_dhanuka_urls() -> Dict[str, Any]:
    try:
        with open(_DHANUKA_URLS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_product_urls_only(urls_data: Dict[str, Any]) -> list[str]:
    """Return only individual product page URLs (exclude category/home/products listing URLs)."""
    if not isinstance(urls_data, dict):
        return []

    urls: list[str] = []
    for key in ("confirmed_products", "additional_products", "individual_products"):
        m = urls_data.get(key)
        if isinstance(m, dict):
            urls.extend([v for v in m.values() if isinstance(v, str)])

    # Newer format: slug_index is a slug->url dict.
    slug_index = urls_data.get("slug_index")
    if isinstance(slug_index, dict):
        urls.extend([v for v in slug_index.values() if isinstance(v, str)])

    # Some projects may only have all_urls populated.
    if not urls:
        raw = urls_data.get("all_urls")
        if isinstance(raw, list):
            urls = [u for u in raw if isinstance(u, str)]

    # Filter to likely product detail pages.
    filtered: list[str] = []
    for u in urls:
        if "dhanuka.com" not in (u or "").lower():
            continue
        pu = urlparse(u)
        path = (pu.path or "").rstrip("/")

        # Exclude listings and category pages.
        if path in ("", "/", "/products"):
            continue
        if path.startswith("/products/") and path in (
            "/products/fungicides",
            "/products/insecticides",
            "/products/herbicides",
            "/products/biologicals",
            "/products/plant-growth-regulators",
            "/products/biostimulants",
            "/products/efficacy-enhancer",
            "/products/bio-fertiliser",
        ):
            continue

        # Must have at least 2 path segments for a detail page.
        segs = [s for s in path.split("/") if s]
        if len(segs) < 2:
            continue

        filtered.append(u)

    # de-dup preserving order
    dedup: list[str] = []
    seen = set()
    for u in filtered:
        if u in seen:
            continue
        seen.add(u)
        dedup.append(u)
    return dedup


def _is_dhanuka_product_detail_url(url: str) -> bool:
    """True only for product *detail* pages (not category/listing)."""
    u = (url or "").strip()
    if not u:
        return False
    pu = urlparse(u)
    if "dhanuka.com" not in (pu.netloc or "").lower():
        return False

    path = (pu.path or "").rstrip("/")
    if not path or path in ("/", "/products"):
        return False

    # Only allow known detail-page prefixes.
    # Dhanuka uses both:
    # - /<category>/<slug>  (e.g. /fungicides/melody-duo)
    # - /products/<slug>    (some single-product pages)
    allowed_detail_prefixes = (
        "/fungicides/",
        "/insecticides/",
        "/herbicides/",
        "/biologicals/",
        "/biostimulants/",
        "/plant-growth-regulators/",
        "/efficacy-enhancer/",
        "/bio-fertiliser/",
        "/product/",
        "/products/",
    )
    if not any(path.startswith(p) for p in allowed_detail_prefixes):
        return False

    # Exclude known listing/category pages.
    if path in (
        "/fungicides",
        "/insecticides",
        "/herbicides",
        "/biologicals",
        "/biostimulants",
        "/plant-growth-regulators",
        "/efficacy-enhancer",
        "/bio-fertiliser",
    ):
        return False

    # /products/<slug> is allowed (2 segments). But reject deeper /products/.../... paths
    # since those are typically category-like or incorrect routes.
    if path.startswith("/products/") and path.count("/") > 2:
        return False

    # Require at least 2 segments (e.g. /fungicides/dhanuka-m-45)
    segs = [s for s in path.split("/") if s]
    return len(segs) >= 2


def _slugify(text: str) -> str:
    """Simple slugify: lowercase, hyphen replace spaces/punct, strip non-alnum/hyphen."""
    import re
    text = text.lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^\w\-]', '', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def _build_dhanuka_url_index() -> Dict[str, str]:
    """Map last-path-segment slug -> canonical product URL from complete_dhanuka_urls.json."""
    urls_data = _read_dhanuka_urls()
    urls = _get_product_urls_only(urls_data)
    idx: Dict[str, str] = {}
    for u in urls:
        try:
            pu = urlparse(u)
            segs = [s for s in (pu.path or "").split("/") if s]
            if not segs:
                continue
            slug = segs[-1].strip().lower()
            if slug and slug not in idx:
                idx[slug] = u
        except Exception:
            continue
    return idx


_DHANUKA_CANONICAL_URL_OVERRIDES: Dict[str, str] = {
    # Some products have multiple routes on dhanuka.com; force the canonical product-detail page.
    # Live /products index currently points these slugs to /biostimulants/...
    "dhanzyme-gold-liq": "https://www.dhanuka.com/biostimulants/dhanzyme-gold-liq",
    "dhanzyme-gold-granules": "https://www.dhanuka.com/biostimulants/dhanzyme-gold-granules",
}


# Ensure knowledge base product URLs are repaired/synced from canonical index.
_sync_knowledge_urls()


def _load_dhanuka_cache() -> Dict[str, Any]:
    try:
        with open(_DHANUKA_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"products": {}, "generated_at": None, "source": ""}


def _save_dhanuka_cache(cache: Dict[str, Any]) -> None:
    with open(_DHANUKA_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# =============================================================================
# SIMPLIFIED DHANUKA CATALOG (use existing dhanuka_detailed_products.json)
# =============================================================================

_DHANUKA_DETAILED_PATH = os.path.join(os.path.dirname(__file__), "dhanuka_detailed_products.json")

def _load_dhanuka_detailed_catalog() -> list[dict]:
    """Load the existing dhanuka_detailed_products.json catalog."""
    try:
        with open(_DHANUKA_DETAILED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def dhanuka_load_catalog(tool_context: ToolContext) -> dict:
    """Load the Dhanuka product catalog (name, url, category) from prompts.py only."""
    catalog: list[dict] = []
    for _, product in (DHANUKA_KNOWLEDGE or {}).items():
        name = (product.get("name") or "").strip()
        url = (product.get("url") or "").strip()
        cat = (product.get("category") or "").strip()
        if not name or not url:
            continue
        if not _is_dhanuka_product_detail_url(url):
            continue
        catalog.append({"name": name, "url": url, "category": cat})

    tool_context.state["temp:dhanuka_catalog"] = catalog
    return {"status": "catalog_loaded", "count": len(catalog), "products": catalog}


def dhanuka_recommend_from_search(tool_context: ToolContext, query: str, top_k: int = 3) -> dict:
    """Recommend Dhanuka products using only prompts.py DHANUKA_KNOWLEDGE (no extra datasets)."""
    try:
        recs = get_dhanuka_recommendations(query or "", top_k=top_k)
    except Exception:
        recs = []

    clean: list[dict] = []
    for p in recs or []:
        url = p.get("url", "")
        if not _is_dhanuka_product_detail_url(url):
            continue
        clean.append({
            "name": p.get("name", ""),
            "url": url,
            "category": p.get("category", ""),
            "active_ingredient": p.get("active_ingredient", ""),
            "why_this_product": p.get("why_this_product", ""),
            "dosage": p.get("dosage", ""),
            "application": p.get("application", ""),
        })

    tool_context.state["temp:dhanuka_recommendations"] = clean
    return {"status": "recommendations_ready", "count": len(clean), "products": clean}


def dhanuka_format_recommendations(tool_context: ToolContext) -> dict:
    """Format last Dhanuka recommendations for display using in-repo formatter."""
    recs = tool_context.state.get("temp:dhanuka_recommendations")
    if not isinstance(recs, list) or not recs:
        return {"status": "empty", "text": ""}
    blocks = []
    for p in recs[:2]:
        try:
            blocks.append(format_dhanuka_recommendation(p))
        except Exception:
            name = p.get("name", "")
            url = p.get("url", "")
            blocks.append(f"**{name}**\n- 🔗 [View Product Details]({url})")
    return {"status": "ok", "text": "\n\n".join(blocks)}


def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "product"


def _infer_category_from_url(url: str) -> str:
    u = (url or "").lower()
    for cat in ("fungicides", "insecticides", "herbicides", "biologicals"):
        if f"/{cat}/" in u:
            return cat
    if "/products/" in u:
        return "products"
    return "unknown"


def _parse_product_page_html(url: str, html_text: str) -> Dict[str, Any]:
    title = ""
    description = ""
    features: list[str] = []
    sections: Dict[str, str] = {}
    dosage = ""
    application = ""
    pack_sizes: list[str] = []

    if BeautifulSoup is None:
        plain = re.sub(r"\s+", " ", html_text or " ").strip()
        return {
            "url": url,
            "title": "",
            "category": _infer_category_from_url(url),
            "description": "",
            "features": [],
            "dosage": "",
            "application": "",
            "pack_sizes": [],
            "sections": {"page_text": plain[:5000]},
        }

    soup = BeautifulSoup(html_text, "html.parser")

    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc.get("content").strip()

    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Basic extraction heuristics for dosage / application / pack sizes.
    joined = "\n".join(lines)
    m = re.search(r"(?i)dosage\s*[:\-]?\s*(.{0,120})", joined)
    if m:
        dosage = m.group(1).strip()
    m = re.search(r"(?i)(application|usage|how to use)\s*[:\-]?\s*(.{0,180})", joined)
    if m:
        application = m.group(2).strip()
    pack_sizes = list(dict.fromkeys(re.findall(r"\b\d+\s*(ml|l|kg|g)\b", joined, flags=re.IGNORECASE)))[:8]

    for ln in lines:
        if ln.startswith("- ") or ln.startswith("•"):
            val = ln.lstrip("-• ").strip()
            if 6 <= len(val) <= 180:
                features.append(val)
    features = list(dict.fromkeys(features))[:20]

    sections["page_text"] = "\n".join(lines[:350])

    return {
        "url": url,
        "title": title,
        "category": _infer_category_from_url(url),
        "description": description,
        "features": features,
        "dosage": dosage,
        "application": application,
        "pack_sizes": pack_sizes,
        "sections": sections,
    }


def dhanuka_scrape_all_products(tool_context: ToolContext, force: bool = False, limit: int = 0) -> dict:
    if not force and os.path.exists(_DHANUKA_CACHE_PATH):
        cache = _load_dhanuka_cache()
        return {
            "status": "cache_exists",
            "path": _DHANUKA_CACHE_PATH,
            "product_count": len(cache.get("products", {})),
        }

    urls_data = _read_dhanuka_urls()
    urls = _get_product_urls_only(urls_data)
    if limit and limit > 0:
        urls = urls[:limit]

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    products: Dict[str, Any] = {}
    errors: list[dict] = []

    for i, url in enumerate(urls, 1):
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                errors.append({"url": url, "status": resp.status_code})
                continue

            parsed = _parse_product_page_html(url, resp.text)
            pid = _slugify(parsed.get("title") or url.rsplit("/", 1)[-1])
            parsed["id"] = pid
            products[pid] = parsed

            time.sleep(0.6)
        except Exception as e:
            errors.append({"url": url, "error": str(e)})

    cache = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": _DHANUKA_URLS_PATH,
        "products": products,
        "errors": errors,
    }
    _save_dhanuka_cache(cache)

    tool_context.state["app:dhanuka_cache_path"] = _DHANUKA_CACHE_PATH
    tool_context.state["app:dhanuka_cache_generated_at"] = cache["generated_at"]

    return {
        "status": "scraped",
        "path": _DHANUKA_CACHE_PATH,
        "product_count": len(products),
        "error_count": len(errors),
    }


def dhanuka_list_products(tool_context: ToolContext) -> dict:
    cache = _load_dhanuka_cache()
    prods = cache.get("products", {})
    items = []
    for pid, p in prods.items():
        items.append({
            "id": pid,
            "title": p.get("title", ""),
            "category": p.get("category", ""),
            "url": p.get("url", ""),
        })
    items = sorted(items, key=lambda x: (x.get("category", ""), x.get("title", "")))
    return {"count": len(items), "products": items, "cache_path": _DHANUKA_CACHE_PATH}


def dhanuka_search_products(tool_context: ToolContext, query: str, top_k: int = 6) -> dict:
    q = (query or "").strip().lower()
    cache = _load_dhanuka_cache()
    prods = cache.get("products", {})

    scored = []
    for pid, p in prods.items():
        hay = " ".join([
            p.get("title", ""),
            p.get("description", ""),
            " ".join(p.get("features", []) or []),
            p.get("category", ""),
            (p.get("sections", {}) or {}).get("page_text", ""),
        ]).lower()

        score = 0
        if not q:
            score = 1
        else:
            for term in q.split():
                if term and term in hay:
                    score += 1

        if score > 0:
            scored.append({
                "id": pid,
                "title": p.get("title", ""),
                "category": p.get("category", ""),
                "url": p.get("url", ""),
                "score": score,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"query": query, "matches": scored[: max(1, min(top_k, 12))]}


def dhanuka_load_product(tool_context: ToolContext, product_id: str) -> dict:
    cache = _load_dhanuka_cache()
    prods = cache.get("products", {})
    if product_id not in prods:
        return {"error": f"Unknown product_id: {product_id}"}

    p = prods[product_id]
    tool_context.state["temp:dhanuka_current_product_id"] = product_id
    tool_context.state["temp:dhanuka_current_product_title"] = p.get("title", "")

    artifact_name = f"dhanuka_{product_id}.json"
    tool_context.save_artifact(artifact_name, genai_types.Part(text=json.dumps(p, ensure_ascii=False)))
    tool_context.state["temp:dhanuka_current_product_artifact"] = artifact_name

    return {
        "status": "loaded",
        "product_id": product_id,
        "title": p.get("title", ""),
        "category": p.get("category", ""),
        "url": p.get("url", ""),
        "artifact": artifact_name,
    }


def dhanuka_build_context(tool_context: ToolContext, query: str, top_k: int = 4) -> dict:
    matches = dhanuka_search_products(tool_context, query=query, top_k=top_k).get("matches", [])
    cache = _load_dhanuka_cache()
    prods = cache.get("products", {})

    # Fallback: if no direct matches (e.g., uncommon crop like pear), still suggest category-appropriate products.
    if not matches:
        ql = (query or "").lower()
        wanted_cat = None
        if any(k in ql for k in ("fung", "blight", "spot", "mildew", "rust", "leaf spot", "फफूंद", "धब्बा")):
            wanted_cat = "fungicides"
        elif any(k in ql for k in ("insect", "pest", "aphid", "borer", "कीट", "कीड़ा")):
            wanted_cat = "insecticides"
        elif any(k in ql for k in ("weed", " खरपत", "घास", "निंदाई")):
            wanted_cat = "herbicides"

        fallback = []
        for pid, p in prods.items():
            if wanted_cat and p.get("category") != wanted_cat:
                continue
            fallback.append({
                "id": pid,
                "title": p.get("title", ""),
                "category": p.get("category", ""),
                "url": p.get("url", ""),
                "score": 1,
            })
        fallback = sorted(fallback, key=lambda x: x.get("title", ""))[: max(1, min(top_k, 6))]
        matches = fallback

    bundle = []
    for m in matches:
        pid = m["id"]
        p = prods.get(pid, {})
        bundle.append({
            "id": pid,
            "title": p.get("title", ""),
            "category": p.get("category", ""),
            "url": p.get("url", ""),  # Actual URL from catalog
            "description": p.get("description", ""),
            "features": (p.get("features", []) or [])[:10],
            "dosage": p.get("dosage", ""),
            "application": p.get("application", ""),
            "pack_sizes": p.get("pack_sizes", []) or [],
        })

    artifact_name = "dhanuka_context.json"
    tool_context.save_artifact(artifact_name, genai_types.Part(text=json.dumps(bundle, ensure_ascii=False)))
    tool_context.state["temp:dhanuka_context_artifact"] = artifact_name
    tool_context.state["temp:dhanuka_context_query"] = query

    return {"status": "context_built", "count": len(bundle), "artifact": artifact_name, "products": matches, "bundle": bundle}


# FunctionTool instances for simplified Dhanuka tools
dhanuka_load_tool = FunctionTool(dhanuka_load_catalog)
dhanuka_recommend_tool = FunctionTool(dhanuka_recommend_from_search)
dhanuka_format_tool = FunctionTool(dhanuka_format_recommendations)

# =============================================================================
# SUB-AGENTS (each with ONE tool only)
# =============================================================================

weather_agent = LlmAgent(
    name="WeatherAgent",
    model="gemini-2.0-flash",
    description="Specialist in getting current weather for Indian locations (city/state/pincode). Always calls get_weather.",
    instruction=WEATHER_AGENT_INSTR,
    tools=[get_weather],
)

search_agent = LlmAgent(
    name="SearchAgent", 
    model="gemini-2.0-flash",
    description="Agricultural research specialist for India using google_search with citations.",
    instruction=SEARCH_AGENT_INSTR,
    tools=[google_search],
)

finance_insurance_agent = LlmAgent(
    name="FinanceInsuranceAgent",
    model="gemini-2.0-flash",
    description="Finance/insurance specialist: KCC, PMFBY, ROI, documents, deadlines (uses google_search).",
    instruction=FINANCE_SEARCHER_INSTR,
    tools=[google_search],
)

post_harvest_agent = LlmAgent(
    name="PostHarvestAgent",
    model="gemini-2.0-flash",
    description="Post-harvest specialist: harvesting, drying, grading, storage, cold chain (uses google_search).",
    instruction=POST_HARVEST_SEARCHER_INSTR,
    tools=[google_search],
)

compliance_safety_agent = LlmAgent(
    name="ComplianceSafetyAgent",
    model="gemini-2.0-flash",
    description="Safety/compliance specialist: PPE, PHI, MRL, pesticide safety (uses google_search).",
    instruction=COMPLIANCE_SAFETY_SEARCHER_INSTR,
    tools=[google_search],
)

machinery_mechanization_agent = LlmAgent(
    name="MachineryMechanizationAgent",
    model="gemini-2.0-flash",
    description="Mechanization specialist: tractors, harvesters, CHC rental, SMAM subsidy (uses google_search).",
    instruction=MACHINERY_MECHANIZATION_SEARCHER_INSTR,
    tools=[google_search],
)

sustainability_regen_agent = LlmAgent(
    name="SustainabilityRegenAgent",
    model="gemini-2.0-flash",
    description="Sustainability specialist: organic farming, ZBNF, regenerative agriculture (uses google_search).",
    instruction=SUSTAINABILITY_REGEN_SEARCHER_INSTR,
    tools=[google_search],
)

# New specialized agents with comprehensive prompts
soil_analyzer_agent = LlmAgent(
    name="SoilAnalyzerAgent",
    model="gemini-2.0-flash",
    description="Soil health specialist: soil test interpretation, NPK recommendations, soil improvement (uses google_search).",
    instruction=SOIL_ANALYZER_SEARCHER_INSTR,
    tools=[google_search],
)

marketing_agent = LlmAgent(
    name="MarketingAgent",
    model="gemini-2.0-flash",
    description="Marketing specialist: mandi prices, MSP, e-NAM, selling guidance, market trends (uses google_search).",
    instruction=MARKETING_SEARCHER_INSTR,
    tools=[google_search],
)

crop_doctor_agent = LlmAgent(
    name="CropDoctorAgent",
    model="gemini-2.0-flash",
    description="Crop health specialist: disease diagnosis, pest identification, treatment recommendations (uses google_search).",
    instruction=CROP_DOCTOR_SEARCHER_INSTR,
    tools=[google_search],
)

plant_growth_agent = LlmAgent(
    name="PlantGrowthAgent",
    model="gemini-2.0-flash",
    description="Plant growth specialist: PGRs, yield optimization, biostimulants, crop enhancement (uses google_search).",
    instruction=PLANT_GROWTH_SEARCHER_INSTR,
    tools=[google_search],
)

# Crop Planning Agent - combines soil suitability + market prices
crop_planning_agent = LlmAgent(
    name="CropPlanningAgent",
    model="gemini-2.0-flash",
    description="Crop planning specialist: best crops for soil, MSP, mandi prices, profitable crop selection (uses google_search).",
    instruction=CROP_COORDINATOR_INSTR,
    tools=[google_search],
)

# Simplified DhanukaImageAgent (uses knowledge base for correct URLs and 1-2 recommendations)
dhanuka_image_agent = LlmAgent(
    name="DhanukaImageAgent",
    model="gemini-2.0-flash",
    description="Multimodal crop diagnosis + Dhanuka product advisor (uses in-repo dataset only).",
    instruction=DHANUKA_IMAGE_AGENT_INSTR,
    tools=[
        dhanuka_load_tool,
        dhanuka_recommend_tool,
    ],
)

# =============================================================================
# MAIN FARMING EXPERT AGENT (uses AgentTool-wrapped sub-agents)
# =============================================================================

farming_agent = LlmAgent(
    name="FarmingExpertAgent",
    model="gemini-2.0-flash",
    description="KisanMitra main farming advisor agent - orchestrates weather, soil, marketing, crop health, and more.",
    instruction=FARMING_AGENT_INSTR,
    tools=[
        AgentTool(agent=weather_agent),
        AgentTool(agent=search_agent),
        AgentTool(agent=soil_analyzer_agent),
        AgentTool(agent=crop_planning_agent),
        AgentTool(agent=marketing_agent),
        AgentTool(agent=crop_doctor_agent),
        AgentTool(agent=plant_growth_agent),
        AgentTool(agent=finance_insurance_agent),
        AgentTool(agent=post_harvest_agent),
        AgentTool(agent=compliance_safety_agent),
        AgentTool(agent=machinery_mechanization_agent),
        AgentTool(agent=sustainability_regen_agent),
        AgentTool(agent=dhanuka_image_agent),
        dhanuka_load_tool,
        dhanuka_recommend_tool,
        dhanuka_format_tool,
    ],
)

# =============================================================================
# MEMORY SERVICE SETUP
# =============================================================================

memory_service = InMemoryMemoryService()

# =============================================================================
# RUNNER (unchanged)
# =============================================================================

APP_NAME = "FarmingApp"
USER_ID = "cli_user"

async def ask_agent(runner: Runner, session_id: str, text: str) -> str:
    content = genai_types.Content(role="user", parts=[genai_types.Part(text=text)])
    final_text = ""

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text = part.text
                        break
            break

    return final_text or "(no response)"

async def main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=farming_agent, 
        app_name=APP_NAME, 
        session_service=session_service,
        memory_service=memory_service
    )

    session_id = f"session_{os.getpid()}"
    
    # Get current temporal context for default location (Delhi)
    default_location = "Delhi"
    temporal_data = get_location_datetime(default_location)
    
    await session_service.create_session(
        app_name=APP_NAME, 
        user_id=USER_ID, 
        session_id=session_id,
        state={
            "user:name": "Farmer", 
            "current_task": "farming_advice",
            "current_date": temporal_data.get("date", ""),
            "current_time": temporal_data.get("time", ""),
            "current_month": temporal_data.get("month", ""),
            "current_season": temporal_data.get("season", ""),
            "timezone": temporal_data.get("timezone", ""),
            "default_location": default_location
        }
    )

    print("=" * 60)
    print("🌾 Farming Expert Agent Running (With Memory Service & Temporal Awareness)")
    print("=" * 60)
    print(f"📍 Current Context: {temporal_data.get('date', '')} ({temporal_data.get('season', '')})")
    print("=" * 60)

    while True:
        user_input = input("\n👤 Ask your farming question (or type 'exit'): ").strip()
        if user_input.lower() == "exit":
            break

        print("\n🤖 Thinking...\n")
        reply = await ask_agent(runner, session_id, user_input)
        print(reply)
        
        # Store conversation in memory after each interaction
        try:
            session = await session_service.get_session(
                app_name=APP_NAME, 
                user_id=USER_ID, 
                session_id=session_id
            )
            await memory_service.add_session_to_memory(session)
        except Exception as e:
            print(f"Note: Memory storage issue: {e}")

if __name__ == "__main__":
    asyncio.run(main())
