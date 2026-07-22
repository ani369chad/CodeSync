import base64
import re
from dataclasses import dataclass

import httpx
from fastapi import HTTPException

GITHUB_API_BASE = "https://api.github.com"

# Matches: https://github.com/{owner}/{repo}/blob/{ref}/{path}
# ref may contain slashes for branch names like "feature/foo", so we greedily
# match everything up to the last path segment as the file path can't be known
# without querying the API. We instead try progressively.
BLOB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<rest>.+)$"
)

RAW_URL_RE = re.compile(
    r"^https?://raw\.githubusercontent\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/(?P<rest>.+)$"
)

LANGUAGE_BY_EXT = {
    "py": "python", "js": "javascript", "jsx": "javascript", "ts": "typescript",
    "tsx": "typescript", "java": "java", "go": "go", "rs": "rust", "rb": "ruby",
    "php": "php", "c": "c", "h": "c", "cpp": "cpp", "hpp": "cpp", "cs": "csharp",
    "swift": "swift", "kt": "kotlin", "md": "markdown", "json": "json",
    "yml": "yaml", "yaml": "yaml", "html": "html", "css": "css", "scss": "scss",
    "sh": "shell", "sql": "sql", "xml": "xml", "dockerfile": "dockerfile",
    "toml": "toml", "vue": "vue", "svelte": "svelte",
}


@dataclass
class ParsedGithubFile:
    owner: str
    repo: str
    ref: str
    path: str


def infer_language(path: str) -> str | None:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return LANGUAGE_BY_EXT.get(ext)


async def parse_github_url(url: str, token: str | None = None) -> ParsedGithubFile:
    """Parse a GitHub blob/raw URL into owner, repo, ref, path.

    Because branch names can contain slashes, we can't split ref/path
    deterministically from the URL alone, so we query the GitHub branches
    API to disambiguate when needed.
    """
    url = url.strip()

    match = BLOB_URL_RE.match(url)
    is_raw = False
    if not match:
        match = RAW_URL_RE.match(url)
        is_raw = True

    if not match:
        raise HTTPException(status_code=400, detail="URL must be a github.com blob URL or raw.githubusercontent.com URL")

    owner = match.group("owner")
    repo = match.group("repo")
    rest = match.group("rest")

    segments = rest.split("/")
    if len(segments) < 2:
        raise HTTPException(status_code=400, detail="Could not parse file path from URL")

    # Fast path: single-segment ref (most common case, e.g. "main" or a full sha)
    candidate_ref = segments[0]
    candidate_path = "/".join(segments[1:])

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15) as client:
        # Try the fast-path ref first.
        resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{candidate_path}",
            params={"ref": candidate_ref},
            headers=headers,
        )
        if resp.status_code == 200:
            return ParsedGithubFile(owner=owner, repo=repo, ref=candidate_ref, path=candidate_path)

        if is_raw:
            raise HTTPException(status_code=404, detail="File not found on GitHub for the given ref")

        # Slow path: branch name contains slashes. Query branches list and
        # find the longest matching prefix.
        branches_resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches",
            params={"per_page": 100},
            headers=headers,
        )
        if branches_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Repository or file not found on GitHub")

        branch_names = sorted((b["name"] for b in branches_resp.json()), key=len, reverse=True)
        for name in branch_names:
            prefix = name + "/"
            if rest.startswith(prefix):
                path = rest[len(prefix):]
                return ParsedGithubFile(owner=owner, repo=repo, ref=name, path=path)

        raise HTTPException(status_code=404, detail="Could not resolve branch/path from URL")


async def fetch_file_content(owner: str, repo: str, ref: str, path: str, token: str | None = None) -> tuple[str, str]:
    """Fetch raw file content and sha via the GitHub Contents API."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
            headers=headers,
        )

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="File not found on GitHub (private repo? log in with GitHub)")
    if resp.status_code == 403:
        raise HTTPException(status_code=403, detail="GitHub API rate limit exceeded or access forbidden")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch file from GitHub")

    data = resp.json()
    if isinstance(data, list) or data.get("type") != "file":
        raise HTTPException(status_code=400, detail="URL does not point to a single file")

    encoded = data.get("content", "")
    encoding = data.get("encoding", "base64")
    if encoding != "base64":
        raise HTTPException(status_code=500, detail=f"Unsupported content encoding: {encoding}")

    content = base64.b64decode(encoded).decode("utf-8", errors="replace")
    return content, data.get("sha", "")


async def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
    resp.raise_for_status()
    payload = resp.json()
    if "access_token" not in payload:
        raise HTTPException(status_code=400, detail=f"GitHub OAuth failed: {payload}")
    return payload["access_token"]


async def fetch_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GITHUB_API_BASE}/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
    resp.raise_for_status()
    return resp.json()
