import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
URL_FILE = SCRIPT_DIR / "spotify_urls.txt"
COOKIE_FILE = SCRIPT_DIR / "cookies.txt"
DOWNLOADS_DIR = SCRIPT_DIR / ("Downloads")
OUTPUT_TEMPLATE = "{artists} - {title}.{output-ext}"


def get_queries(source):
    """Read Spotify URLs from a text file or use a single URL directly."""
    if source.startswith(("https://", "http://")):
        return [source]

    source_file = Path(source)
    with source_file.open(encoding="utf-8-sig") as file:
        queries = [
            line.strip()
            for line in file
            if line.strip() and not line.lstrip().startswith("#")
        ]

    if not queries:
        raise ValueError(f"No Spotify URLs found in {source_file}.")

    return queries


def get_link_folder(url, index):
    """Build a safe, recognizable folder name from a Spotify URL."""
    parts = [part for part in urlsplit(url).path.split("/") if part]
    for kind in ("playlist", "album", "track", "artist", "episode", "show"):
        if kind in parts:
            kind_index = parts.index(kind)
            if kind_index + 1 < len(parts):
                identifier = parts[kind_index + 1]
                folder = re.sub(r"[^A-Za-z0-9_-]+", "_", identifier).strip("_")
                if folder:
                    return f"{kind}-{folder[:80]}"

    return f"link-{index:03d}"


def download_with_spotdl(queries, cookie_path=None):
    """Run spotDL for Spotify URLs from a file or a public playlist."""
    spotdl_path = shutil.which("spotdl")
    if not spotdl_path:
        raise RuntimeError(
            "spotdl was not found. Install it first, then ensure it is on your PATH."
        )

    if cookie_path and cookie_path.is_file():
        print("[*] Using the supplied cookie file.")
    else:
        print("[*] No valid cookies.txt found; continuing without it.")

    print(f"[*] Starting downloads for {len(queries)} Spotify URL(s).")
    for index, url in enumerate(queries, start=1):
        output_dir = DOWNLOADS_DIR / get_link_folder(url, index)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(output_dir / OUTPUT_TEMPLATE)
        command = [
            spotdl_path,
            "download",
            url,
            "--format",
            "m4a",
            "--output",
            output_template,
        ]

        if cookie_path and cookie_path.is_file():
            command.extend(["--cookie-file", str(cookie_path)])

        print(f"[*] Starting: {url}")
        print(f"[*] Saving to: {output_dir}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        assert process.stdout is not None

        for line in process.stdout:
            print(line, end="")

        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                f"spotDL exited with code {return_code} for {url}."
            )

    print("\n[+] Download process finished successfully.")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Download tracks from Spotify URLs in a text file or from a "
            "public Spotify playlist."
        )
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=str(URL_FILE),
        help=(
            "text file with one Spotify URL per line, or a single public "
            f"Spotify URL (default: {URL_FILE.name})"
        ),
    )
    args = parser.parse_args()

    queries = get_queries(args.source)
    download_with_spotdl(queries, COOKIE_FILE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[-] Cancelled by user.")
        sys.exit(130)
    except Exception as error:
        print(f"\n[-] Error: {error}")
        sys.exit(1)