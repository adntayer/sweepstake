"""Download and cache team logos from football-logos.cc."""

from __future__ import annotations

import json
import os
import re
import time

import requests

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://football-logos.cc/",
}


def _norm(path: str) -> str:
    return os.path.normpath(path)


def logos_dir(config: ChampionshipConfig) -> str:
    """Return the logo cache directory for a championship."""
    d = _norm(os.path.join("src", "championships", config.id, "logos"))
    os.makedirs(d, exist_ok=True)
    return d


def _slugify(text: str) -> str:
    """Convert team name to URL-friendly slug."""
    s = text.lower().strip()
    s = s.replace("ü", "u").replace("é", "e").replace("í", "i").replace("ó", "o").replace("á", "a")
    s = s.replace("ã", "a").replace("õ", "o").replace("ç", "c").replace("â", "a").replace("ê", "e")
    s = s.replace("ô", "o").replace("ú", "u").replace("à", "a")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def logo_local_path(team_en: str, config: ChampionshipConfig) -> str:
    """Return the local cached logo path for a team."""
    return _norm(os.path.join(logos_dir(config), f"{_slugify(team_en)}.png"))


def logo_local_path_pt(team_pt: str, config: ChampionshipConfig) -> str:
    """Return the local cached logo path for a team using Portuguese name."""
    return _norm(os.path.join(logos_dir(config), f"{_slugify(team_pt)}.png"))


def logo_url_to_local(logo_url: str, team_en: str, config: ChampionshipConfig) -> str | None:
    """Download a logo from a URL and cache it locally.

    Returns the local path if successful, None otherwise.
    """
    local_path = logo_local_path(team_en, config)

    if os.path.exists(local_path):
        return local_path

    try:
        resp = requests.get(logo_url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            print_colored(f"  {team_en}: not an image ({content_type})", "yellow")
            return None
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(resp.content)
        print_colored(f"  {team_en}: cached ({len(resp.content)} bytes)", "green")
        time.sleep(0.25)
        return local_path
    except requests.RequestException as e:
        print_colored(f"  {team_en}: download failed ({e})", "red")
        return None


def _extract_content_url(html: str) -> str | None:
    """Extract the contentUrl from a team page's JSON-LD."""
    for m in re.finditer(r'"contentUrl"\s*:\s*"([^"]+)"', html):
        return m.group(1)
    return None


def _find_team_pages(html: str) -> dict[str, str]:
    """Extract team slug -> team page URL from tournament page HTML."""
    pages: dict[str, str] = {}

    # Standard pattern: /{slug}/{slug}-national-team/
    for m in re.finditer(
        r'href="(/([a-z0-9-]+)/([a-z0-9-]+-national-team)/)"',
        html,
    ):
        pages[m.group(2)] = f"https://football-logos.cc{m.group(1)}"

    # Dutch national team: /netherlands/dutch-national-team/
    for m in re.finditer(
        r'href="(/([a-z0-9-]+)/(dutch-national-team)/)"',
        html,
    ):
        pages[m.group(2)] = f"https://football-logos.cc{m.group(1)}"

    # Portuguese federation: /portugal/portuguese-football-federation/
    for m in re.finditer(
        r'href="(/([a-z0-9-]+)/(portuguese-football-federation)/)"',
        html,
    ):
        pages[m.group(2)] = f"https://football-logos.cc{m.group(1)}"

    return pages


def fetch_all_logos(config: ChampionshipConfig, force: bool = False) -> None:
    """Download and cache all team logos.

    For teams with a `logo` URL in the YAML config, downloads directly.
    For teams without, scrapes football-logos.cc to discover the URL.
    """
    to_fetch: list[str] = []
    for en_name in config.team_name_mapping:
        if force or not os.path.exists(logo_local_path(en_name, config)):
            to_fetch.append(en_name)

    if not to_fetch:
        teams = len(config.team_name_mapping)
        print_colored(f"All {teams} team logos already cached. Use --force to re-download.", "green")
        copy_logos_to_html(logos_dir(config), os.path.join(config.reports_dir, "html", "logos"))
        return

    # --- Phase 1: use YAML logo URLs directly ---
    from_config: list[str] = []
    for en_name in to_fetch[:]:
        url = config.team_logos.get(en_name, "")
        if url:
            to_fetch.remove(en_name)
            from_config.append(en_name)
            if logo_url_to_local(url, en_name, config):
                print_colored(f"  {en_name}: cached from YAML URL", "green")
            else:
                print_colored(f"  {en_name}: failed to download from YAML URL", "yellow")

    if not to_fetch:
        total = len(config.team_name_mapping)
        done = len(config.team_name_mapping) - len(to_fetch)
        print_colored(f"Processed logos for {done}/{total} teams", "green")
        return

    # --- Phase 2: scrape football-logos.cc for remaining teams ---
    if not config.logo_scrape_url:
        raise ValueError("logo_scrape_url is not configured")
    tournament_url = config.logo_scrape_url
    print_colored(f"Fetching team list from {tournament_url}", "blue")

    try:
        resp = requests.get(tournament_url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print_colored(f"Failed to fetch tournament page: {e}", "red")
        return

    team_pages = _find_team_pages(resp.text)
    if not team_pages:
        print_colored("No team links found on the page.", "yellow")
        return

    print_colored(f"Found {len(team_pages)} team links on the page", "green")

    override_slug = dict(config.logo_slug_overrides) if config.logo_slug_overrides else {
        "korea-republic": "south-korea",
        "czechia": "czech-republic",
        "turkiye": "turkey",
        "ir-iran": "iran",
        "curaçao": "curacao",
        "côte-d-ivoire": "cote-d-ivoire",
    }
    slug_to_en: dict[str, str] = {}
    for en_name in config.team_name_mapping:
        slug = override_slug.get(_slugify(en_name), _slugify(en_name))
        slug_to_en[slug] = en_name

    found = 0
    for slug, page_url in sorted(team_pages.items()):
        en_name = slug_to_en.get(slug)
        if en_name is None or en_name not in to_fetch:
            continue

        local_path = logo_local_path(en_name, config)
        if not force and os.path.exists(local_path):
            found += 1
            continue

        try:
            page_resp = requests.get(page_url, headers=_HEADERS, timeout=20)
            page_resp.raise_for_status()
        except requests.RequestException as e:
            print_colored(f"  {en_name}: failed to fetch team page ({e})", "yellow")
            time.sleep(0.5)
            continue

        content_url = _extract_content_url(page_resp.text)
        if content_url:
            logo_url_to_local(content_url, en_name, config)
            found += 1
        else:
            print_colored(f"  {en_name}: no contentUrl found on team page", "yellow")

        time.sleep(0.3)

    total = len(config.team_name_mapping)
    print_colored(f"Processed logos for {len(from_config) + found}/{total} teams", "green")
    copy_logos_to_html(logos_dir(config), os.path.join(config.reports_dir, "html", "logos"))

def logo_img_html(team_pt: str, team_en: str, config: ChampionshipConfig) -> str:
    """Return an <img> tag HTML for a team's logo, or empty string if not cached."""
    pt_path = logo_local_path(team_en, config)
    if os.path.exists(pt_path):
        rel = os.path.relpath(pt_path, start=config.reports_dir + "/html").replace("\\", "/")
        return f'<img src="{rel}" alt="{team_pt}" class="team-logo" loading="lazy">'
    return ""

def _team_logo_tag(team_name: str, config: ChampionshipConfig, cls: str, start: str, *, use_en: bool = False) -> str:
    """Return <img> tag for a team's logo based on start directory depth."""
    if use_en:
        en = team_name
    else:
        rev = {v: k for k, v in config.team_name_mapping.items()}
        en = rev.get(team_name, team_name)

    # Cria o nome do arquivo limpo (ex: "canada.png")
    filename = f"{_slugify(en)}.png"

    # Força barras para frente para normalizar Windows/Linux
    normalized_start = start.replace("\\", "/")

    # Isola o caminho a partir da pasta 'html'
    if "/html" in normalized_start:
        relative_part = normalized_start.split("/html")[-1].strip("/")
    else:
        relative_part = ""

    # Define o prefixo baseado no número de subpastas reais
    if not relative_part:
        prefix = ""                # Raiz (html/index.html) -> logos/
    else:
        depth = len(relative_part.split("/"))
        if depth == 1:
            prefix = "../"         # 1 nível (html/times/Canadá.html) -> ../logos/
        else:
            prefix = "../../"      # 2 níveis (html/jogos/1afase/jogo.html) -> ../../logos/

    # Monta o caminho final
    rel = f"{prefix}logos/{filename}"

    return f'<img src="{rel}" alt="{en}" class="{cls}" loading="lazy">'



def copy_logos_to_html(logo_dir_source: str, html_dir_dest: str) -> None:
    """
    Syncs all PNG logos from the source directory to the target HTML directory.

    Removes any stale PNG files in the destination that no longer exist in the source,
    then copies over all current source files. This ensures no orphaned old logos remain.
    """
    print_colored("--- Syncing Logos to HTML Directory ---", "sand")

    # Ensure destination directory exists
    os.makedirs(html_dir_dest, exist_ok=True)

    try:
        source_files = set(f for f in os.listdir(logo_dir_source) if f.lower().endswith('.png'))
    except FileNotFoundError:
        print_colored(f"[CRITICAL ERROR] Source directory not found: {logo_dir_source}", "red")
        return
    except Exception as e:
        print_colored(f"[CRITICAL ERROR] Failed to read source directory: {e}", "red")
        return

    # Remove stale PNG files from destination that are no longer in source
    try:
        for f in os.listdir(html_dir_dest):
            if f.lower().endswith('.png') and f not in source_files:
                os.remove(_norm(os.path.join(html_dir_dest, f)))
                print_colored(f"  Removed stale: {f}", "yellow")
    except Exception as e:
        print_colored(f"  [WARN] Failed to clean destination: {e}", "yellow")

    # Copy all source files to destination
    copied_count = 0
    for filename in sorted(source_files):
        src_path = _norm(os.path.join(logo_dir_source, filename))
        dest_path = _norm(os.path.join(html_dir_dest, filename))

        try:
            with open(src_path, "rb") as f_in:
                content = f_in.read()
            with open(dest_path, "wb") as f_out:
                f_out.write(content)
            copied_count += 1
        except Exception as e:
            print_colored(f"  [ERROR] Failed to copy {filename}: {e}", "red")

    print_colored(f"--- Logo Sync Finished. {copied_count}/{len(source_files)} files copied. ---", "sand")
