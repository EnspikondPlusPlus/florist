"""Research-tool layer — every literature / repo / post lookup goes through here.

Chain for papers (``settings.research_order``):
alphaXiv → OpenAlex → arXiv → Semantic Scholar → coding agent's own web tools.
A tool that errors or rate-limits is skipped and the next one answers; every
successful call is cached in ``research_cache`` (TTL ``cache_ttl_days``).
Repos come from the GitHub search API, posts from Hacker News (Algolia).
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import httpx
from pydantic import BaseModel, Field

from . import config
from .schemas import now_iso
from .store import db

UA = "Florist/0.1 (local-first ideation suite)"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class Hit(BaseModel):
    tool: str
    kind: str = "paper"  # paper | repo | post | web
    external_id: str = ""
    title: str
    url: str = ""
    abstract: str = ""
    year: int | None = None
    published: str = ""
    authors: list[str] = Field(default_factory=list)
    venue: str = ""
    citations: int | None = None
    stars: int | None = None

    def key(self) -> str:
        if self.kind == "paper":
            arx = arxiv_id(self.url) or arxiv_id(self.external_id)
            if arx:
                return f"arxiv:{arx}"
            return "title:" + re.sub(r"[^a-z0-9]", "", self.title.lower())[:80]
        return self.url or f"{self.tool}:{self.external_id}"


class ToolError(RuntimeError):
    pass


def arxiv_id(s: str) -> str:
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", s or "")
    return m.group(1) if m else ""


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent": UA}, follow_redirects=True)


def _get_json(url: str, params: dict | None = None, headers: dict | None = None) -> Any:
    with _client() as c:
        r = c.get(url, params=params, headers=headers or {})
    if r.status_code == 429:
        raise ToolError("rate limited")
    if r.status_code >= 400:
        raise ToolError(f"HTTP {r.status_code}")
    return r.json()


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def cached(tool: str, query: str, fn: Callable[[], list[Hit]], ttl_days: int | None = None) -> list[Hit]:
    key = hashlib.sha256(f"{tool}\x00{query}".encode()).hexdigest()
    ttl = ttl_days if ttl_days is not None else config.get().cache_ttl_days
    row = db.q1("SELECT created, payload FROM research_cache WHERE key=?", (key,))
    if row:
        created = datetime.fromisoformat(row["created"])
        if datetime.now(timezone.utc) - created < timedelta(days=ttl):
            return [Hit.model_validate(h) for h in json.loads(row["payload"])]
    hits = fn()
    db.ex(
        "INSERT OR REPLACE INTO research_cache(key, tool, query, created, payload) VALUES (?,?,?,?,?)",
        (key, tool, query, now_iso(), json.dumps([h.model_dump() for h in hits])),
    )
    return hits


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def alphaxiv(query: str, limit: int = 8, since: str | None = None, strategy: str = "embedding") -> list[Hit]:
    params = {"q": query, "prioritize": "recency" if since else "default"}
    if since:
        params["publishedAfter"] = since
    data = _get_json(f"https://api.alphaxiv.org/search/v2/paper/discover/{strategy}", params)
    hits = []
    for p in (data or [])[:limit]:
        pid = p.get("paperId", "")
        date = (p.get("publicationDate") or "")[:10]
        hits.append(
            Hit(
                tool="alphaxiv", external_id=pid, title=p.get("title", "").strip(),
                url=f"https://www.alphaxiv.org/abs/{pid}", abstract=(p.get("abstract") or "")[:1500],
                published=date, year=int(date[:4]) if date[:4].isdigit() else None,
            )
        )
    return hits


def openalex(query: str, limit: int = 8, since: str | None = None) -> list[Hit]:
    params: dict[str, Any] = {
        "search": query, "per_page": limit,
        "select": "id,doi,title,publication_year,publication_date,cited_by_count,authorships,"
                  "primary_location,abstract_inverted_index",
    }
    if since:
        params["filter"] = f"from_publication_date:{since}"
    key = config.key_for("openalex")
    if key:
        params["api_key"] = key
    data = _get_json("https://api.openalex.org/works", params)
    hits = []
    for w in data.get("results", [])[:limit]:
        loc = w.get("primary_location") or {}
        src = (loc.get("source") or {}).get("display_name") or ""
        url = loc.get("landing_page_url") or w.get("doi") or w.get("id", "")
        hits.append(
            Hit(
                tool="openalex", external_id=w.get("id", ""), title=(w.get("title") or "").strip(),
                url=url, abstract=_unindex(w.get("abstract_inverted_index"))[:1500],
                year=w.get("publication_year"), published=w.get("publication_date") or "",
                authors=[a["author"]["display_name"] for a in (w.get("authorships") or [])[:6] if a.get("author")],
                venue=src, citations=w.get("cited_by_count"),
            )
        )
    return hits


def openalex_count(query: str, since: str | None = None) -> int:
    params: dict[str, Any] = {"search": query, "per_page": 1, "select": "id"}
    if since:
        params["filter"] = f"from_publication_date:{since}"
    data = _get_json("https://api.openalex.org/works", params)
    return int((data.get("meta") or {}).get("count") or 0)


def _unindex(inv: dict | None) -> str:
    if not inv:
        return ""
    pos: list[tuple[int, str]] = [(i, w) for w, idx in inv.items() for i in idx]
    return " ".join(w for _, w in sorted(pos))


_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def arxiv(query: str, limit: int = 8, since: str | None = None) -> list[Hit]:
    terms = " AND ".join(f"all:{t}" for t in re.findall(r"[A-Za-z0-9\-]+", query)[:6]) or f"all:{query}"
    params = {"search_query": terms, "max_results": limit * 2 if since else limit,
              "sortBy": "submittedDate" if since else "relevance"}
    with _client() as c:
        r = c.get("https://export.arxiv.org/api/query", params=params)
    if r.status_code >= 400:
        raise ToolError(f"HTTP {r.status_code}")
    root = ET.fromstring(r.text)
    hits = []
    for e in root.findall("a:entry", _ATOM):
        published = (e.findtext("a:published", "", _ATOM) or "")[:10]
        if since and published and published < since:
            continue
        url = e.findtext("a:id", "", _ATOM)
        hits.append(
            Hit(
                tool="arxiv", external_id=arxiv_id(url), title=" ".join((e.findtext("a:title", "", _ATOM)).split()),
                url=url, abstract=" ".join((e.findtext("a:summary", "", _ATOM)).split())[:1500],
                published=published, year=int(published[:4]) if published[:4].isdigit() else None,
                authors=[a.findtext("a:name", "", _ATOM) for a in e.findall("a:author", _ATOM)][:6],
            )
        )
    return hits[:limit]


def semantic_scholar(query: str, limit: int = 8, since: str | None = None) -> list[Hit]:
    params: dict[str, Any] = {"query": query, "limit": limit,
                              "fields": "title,year,abstract,url,citationCount,venue,authors,externalIds,publicationDate"}
    if since:
        params["publicationDateOrYear"] = f"{since}:"
    key = config.key_for("semantic_scholar")
    data = _get_json("https://api.semanticscholar.org/graph/v1/paper/search", params,
                     headers={"x-api-key": key} if key else None)
    hits = []
    for p in data.get("data", [])[:limit]:
        ext = p.get("externalIds") or {}
        url = f"https://arxiv.org/abs/{ext['ArXiv']}" if ext.get("ArXiv") else (p.get("url") or "")
        hits.append(
            Hit(
                tool="semantic_scholar", external_id=p.get("paperId", ""), title=p.get("title") or "",
                url=url, abstract=(p.get("abstract") or "")[:1500], year=p.get("year"),
                published=p.get("publicationDate") or "", venue=p.get("venue") or "",
                citations=p.get("citationCount"), authors=[a.get("name", "") for a in (p.get("authors") or [])[:6]],
            )
        )
    return hits


def github(query: str, limit: int = 6, since: str | None = None) -> list[Hit]:
    q = query + (f" pushed:>={since}" if since else "")
    token = config.key_for("github")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = _get_json("https://api.github.com/search/repositories",
                     {"q": q, "sort": "stars", "per_page": limit}, headers=headers)
    hits = []
    for r in data.get("items", [])[:limit]:
        pushed = (r.get("pushed_at") or "")[:10]
        hits.append(
            Hit(
                tool="github", kind="repo", external_id=r.get("full_name", ""), title=r.get("full_name", ""),
                url=r.get("html_url", ""), abstract=(r.get("description") or "")[:600], published=pushed,
                year=int(pushed[:4]) if pushed[:4].isdigit() else None, stars=r.get("stargazers_count"),
                venue=r.get("language") or "",
            )
        )
    return hits


def hackernews(query: str, limit: int = 5, since: str | None = None) -> list[Hit]:
    params: dict[str, Any] = {"query": query, "tags": "story", "hitsPerPage": limit}
    if since:
        ts = int(datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp())
        params["numericFilters"] = f"created_at_i>{ts}"
    data = _get_json("https://hn.algolia.com/api/v1/search", params)
    hits = []
    for h in data.get("hits", [])[:limit]:
        created = (h.get("created_at") or "")[:10]
        hits.append(
            Hit(
                tool="hackernews", kind="post", external_id=str(h.get("objectID")), title=h.get("title") or "",
                url=h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                abstract=f"{h.get('points', 0)} points, {h.get('num_comments', 0)} comments on Hacker News",
                published=created, year=int(created[:4]) if created[:4].isdigit() else None,
            )
        )
    return hits


def agent_web(query: str, limit: int = 6, since: str | None = None) -> list[Hit]:
    """Last resort: ask a coding-agent backend (Claude Code) to use its own web search tools."""
    from . import gateway
    from .schemas import Model

    model = config.get().models.fast
    if gateway.backend_of(model) != "claude-code":
        cc = [m for m in (config.get().models.strong, config.get().models.default)
              if gateway.backend_of(m) == "claude-code"]
        if not cc:
            raise ToolError("agent_web needs a claude-code model configured")
        model = cc[0]

    class WebHit(Model):
        title: str
        url: str
        snippet: str = ""
        year: int | None = None

    class WebHits(Model):
        hits: list[WebHit]

    res = gateway.complete(
        gateway.Call(step="ground", model=model, allow_web=True),
        "You are a research librarian. Use web search to find real, existing work. Never invent URLs.",
        f"Find up to {limit} papers, repositories or posts about: {query}"
        + (f" published after {since}" if since else "")
        + ". Return title, URL, a one-sentence snippet and the year.",
        WebHits,
    )
    return [Hit(tool="agent_web", kind="web", title=h.title, url=h.url, abstract=h.snippet, year=h.year)
            for h in res.hits[:limit]]


PAPER_TOOLS: dict[str, Callable[..., list[Hit]]] = {
    "alphaxiv": alphaxiv,
    "openalex": openalex,
    "arxiv": arxiv,
    "semantic_scholar": semantic_scholar,
    "agent_web": agent_web,
}
ALL_TOOLS: dict[str, Callable[..., list[Hit]]] = {**PAPER_TOOLS, "github": github, "hackernews": hackernews}


# ---------------------------------------------------------------------------
# Front door
# ---------------------------------------------------------------------------


def search(query: str, kind: str = "paper", limit: int = 6, since: str | None = None,
           tool: str | None = None, log: Callable[[str], None] | None = None) -> list[Hit]:
    """Search with fallback; returns de-duplicated hits from the first tool that answers."""
    if tool:
        chain = [tool]
    elif kind == "repo":
        chain = ["github"]
    elif kind == "post":
        chain = ["hackernews"]
    else:
        chain = list(config.get().research_order)
    errors = []
    for name in chain:
        fn = ALL_TOOLS.get(name)
        if not fn:
            continue
        try:
            hits = cached(name, json.dumps([query, limit, since]), lambda fn=fn: fn(query, limit=limit, since=since))
        except Exception as e:  # rate limit, network, parse: fall back to the next tool
            errors.append(f"{name}: {e}")
            if log:
                log(f"{name} unavailable ({e}); falling back")
            continue
        if hits:
            return _dedupe(hits)
    if errors and log:
        log("no research tool answered: " + "; ".join(errors))
    return []


def crowdedness(query: str, months: int = 18) -> dict[str, Any]:
    """Quantitative crowdedness signal: how many works match, and how many are recent."""
    since = (datetime.now(timezone.utc) - timedelta(days=30 * months)).date().isoformat()

    def count() -> list[Hit]:
        total = openalex_count(query)
        recent = openalex_count(query, since)
        return [Hit(tool="openalex", title="count", abstract=json.dumps({"total": total, "recent": recent}))]

    try:
        hit = cached("openalex_count", json.dumps([query, since]), count)[0]
        data = json.loads(hit.abstract)
    except Exception as e:
        return {"total": None, "recent": None, "since": since, "error": str(e)}
    return {**data, "since": since}


def _dedupe(hits: list[Hit]) -> list[Hit]:
    seen, out = set(), []
    for h in hits:
        k = h.key()
        if k in seen or not h.title:
            continue
        seen.add(k)
        out.append(h)
    return out


def fetch_page_meta(url: str) -> dict[str, str]:
    """Title + description for 'save a link to Florist'."""
    with _client() as c:
        r = c.get(url)
    html = r.text[:200_000]

    def meta(name: str) -> str:
        m = re.search(
            rf'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]+content=["\']([^"\']+)', html, re.I
        ) or re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{name}["\']', html, re.I)
        return m.group(1).strip() if m else ""

    title = meta("og:title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = " ".join(m.group(1).split()) if m else url
    desc = meta("og:description") or meta("description")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = " ".join(re.sub(r"<[^>]+>", " ", text).split())[:4000]
    return {"title": title, "description": desc, "text": text}
