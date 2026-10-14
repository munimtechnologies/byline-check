#!/usr/bin/env python3
"""byline-check: a verification worksheet for editors vetting a freelance pitch.

It does not decide whether a writer is real, and it does no AI-text detection.
It runs the checks editors used after the fake-freelancer cases of 2025-2026
(claimed clips, bylines, removed stories, domain age, reused quotes, who the
pitch really came from, bylines already documented as fake or impersonated)
and lists what a person still has to verify. Standard library only.

    python byline_check.py --name "Jane Doe" --pitch pitch.eml --draft draft.txt
    python byline_check.py --name "Jane Doe" --clip https://example.com/story --json
"""

import argparse
import email
import http.client
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from email import policy
from email.utils import getaddresses
from html.parser import HTMLParser

__version__ = "0.3.0"

USER_AGENT = "byline-check/%s (+https://github.com/munimv2/byline-check)" % __version__
TIMEOUT = 20
MAX_BYTES = 4_000_000
MAX_CLIPS = 15
MAX_DOMAINS = 5
MAX_SITES = 3
NEW_DOMAIN_DAYS = 365
RDAP_URL = "https://rdap.org/domain/"
CDX_URL = "https://web.archive.org/cdx/search/cdx?"

FREE_MAIL = frozenset({
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "outlook.com",
    "hotmail.com", "hotmail.co.uk", "live.com", "msn.com", "icloud.com", "me.com",
    "mac.com", "aol.com", "proton.me", "protonmail.com", "pm.me", "gmx.com",
    "gmx.net", "gmx.de", "web.de", "mail.com", "yandex.com", "yandex.ru",
    "zoho.com", "fastmail.com", "tutanota.com", "tuta.io", "hey.com", "qq.com",
    "163.com",
})

# Outlet names a pitch may claim, matched case-sensitively, and the domains a
# clip from that outlet would live on. One-word names that are also common
# words (Science, Nature, Time, Vice) are left out to avoid false matches.
OUTLETS = [
    ("WIRED", ("wired.com", "wired.co.uk")),
    ("Wired", ("wired.com", "wired.co.uk")),
    ("Business Insider", ("businessinsider.com",)),
    ("New York Times", ("nytimes.com",)),
    ("Washington Post", ("washingtonpost.com",)),
    ("Wall Street Journal", ("wsj.com",)),
    ("Los Angeles Times", ("latimes.com",)),
    ("The Guardian", ("theguardian.com",)),
    ("The Atlantic", ("theatlantic.com",)),
    ("The New Yorker", ("newyorker.com",)),
    ("The Economist", ("economist.com",)),
    ("Financial Times", ("ft.com",)),
    ("The Independent", ("independent.co.uk",)),
    ("The Telegraph", ("telegraph.co.uk",)),
    ("Daily Mail", ("dailymail.co.uk",)),
    ("BBC", ("bbc.com", "bbc.co.uk")),
    ("Reuters", ("reuters.com",)),
    ("Associated Press", ("apnews.com",)),
    ("Bloomberg", ("bloomberg.com",)),
    ("Forbes", ("forbes.com",)),
    ("Fortune", ("fortune.com",)),
    ("Fast Company", ("fastcompany.com",)),
    ("Quartz", ("qz.com",)),
    ("Vox", ("vox.com",)),
    ("VICE", ("vice.com",)),
    ("Slate", ("slate.com",)),
    ("Salon", ("salon.com",)),
    ("HuffPost", ("huffpost.com",)),
    ("BuzzFeed", ("buzzfeed.com", "buzzfeednews.com")),
    ("Politico", ("politico.com", "politico.eu")),
    ("POLITICO", ("politico.com", "politico.eu")),
    ("Axios", ("axios.com",)),
    ("NPR", ("npr.org",)),
    ("CNN", ("cnn.com",)),
    ("NBC News", ("nbcnews.com",)),
    ("CBS News", ("cbsnews.com",)),
    ("ABC News", ("abcnews.go.com", "abc.net.au")),
    ("Al Jazeera", ("aljazeera.com",)),
    ("ProPublica", ("propublica.org",)),
    ("Mother Jones", ("motherjones.com",)),
    ("The Verge", ("theverge.com",)),
    ("Ars Technica", ("arstechnica.com",)),
    ("TechCrunch", ("techcrunch.com",)),
    ("MIT Technology Review", ("technologyreview.com",)),
    ("Scientific American", ("scientificamerican.com",)),
    ("New Scientist", ("newscientist.com",)),
    ("Undark", ("undark.org",)),
    ("Knowable", ("knowablemagazine.org",)),
    ("Nautilus", ("nautil.us",)),
    ("Aeon", ("aeon.co",)),
    ("SFGate", ("sfgate.com",)),
    ("Index on Censorship", ("indexoncensorship.org",)),
    ("Globe and Mail", ("theglobeandmail.com",)),
    ("Toronto Star", ("thestar.com",)),
    ("Ottawa Citizen", ("ottawacitizen.com",)),
    ("Montreal Gazette", ("montrealgazette.com",)),
    ("National Post", ("nationalpost.com",)),
    ("CBC", ("cbc.ca",)),
    ("The Cut", ("thecut.com",)),
    ("Dwell", ("dwell.com",)),
    ("Elle", ("elle.com",)),
    ("Marie Claire", ("marieclaire.com", "marieclaire.co.uk")),
    ("Cosmopolitan", ("cosmopolitan.com",)),
    ("Vogue", ("vogue.com", "vogue.co.uk")),
    ("Rolling Stone", ("rollingstone.com",)),
    ("Refinery29", ("refinery29.com",)),
]

# Patterns seen in documented fake-freelancer cases. A match is a reason to
# verify, never proof: plenty of real writers use PayPal or prefer email.
RED_FLAGS = [
    (
        "email-only",
        "Email-only contact",
        "The fake 'Daniel Robson' told the Ottawa Citizen he could only communicate by email; "
        "Science's news team only ever emailed the impostor of a real science writer. "
        "Insist on a live call or a meeting.",
        [
            r"\b(?:only|just)\s+(?:communicate\s+|talk\s+|correspond\s+)?(?:by|via|over|through)\s+e-?mail\b",
            r"\b(?:can(?:not|'t|’t)|unable\s+to|won(?:'t|’t))\s+(?:do|join|make|take|have|hop\s+on)\s+"
            r"(?:a\s+|the\s+|any\s+)?(?:phone\s+|video\s+|zoom\s+|quick\s+)?(?:call|chat|meeting)\b",
            r"\b(?:can(?:not|'t|’t)|unable\s+to)\s+(?:meet|talk|speak)\s+"
            r"(?:in\s+person|by\s+phone|on\s+the\s+phone|on\s+video|right\s+now)\b",
            r"\bprefer\s+(?:to\s+)?(?:keep\s+(?:it|things)|stick|stay)\s+(?:to|on|over|via|by)\s+e-?mail\b",
            r"\bprefer\s+e-?mail\b",
        ],
    ),
    (
        "payment",
        "Payment outside the normal system",
        "WIRED's 'Margaux Blanchard' could not give enough details for WIRED's payments system "
        "and insisted on PayPal or a check. Pay only through your usual system with verified details.",
        [
            r"\bpay\s?pal\b",
            r"\b(?:by|via|with)\s+(?:a\s+)?(?:paper\s+|mailed\s+)?(?:check|cheque)\b",
            r"\bgift\s?cards?\b",
            r"\b(?:crypto(?:currency)?|bitcoin|btc|usdt|tether)\b",
        ],
    ),
]

# Bylines documented in published reporting as invented personas, and real
# writers documented as impersonated. A name match is never proof: real people
# share these names. Add a case only with a public source.
OPENAI_2026 = "https://openai.com/index/disrupting-ai-enabled-false-front-operations/"
BOGUS_BYLINES = ("one of seven fake journalist personas in the 'Bogus Bylines' operation that OpenAI "
                 "reported on 8 Oct 2026; almost 100 articles ran under them in about a dozen "
                 "outlets between July 2025 and October 2026.")
WE_NEWS = ("an AI-generated staff persona of the We News site, reported by The Canadian Press on "
           "3 Oct 2026.")
WE_NEWS_SOURCE = "https://www.cp24.com/news/canada/2026/10/03/byline-or-bot-ai-generated-journalists-start-to-appear-in-canada/"
PERSONAS = [
    ("Margaux Blanchard", "invented",
     "stories WIRED, Business Insider and other outlets removed in 2025; the writer could not "
     "be shown to exist.",
     "https://pressgazette.co.uk/publishers/digital-journalism/margaux-blanchard-wired-ai-editors-journalist/"),
    ("Daniel Robson", "invented",
     "a persona whose columns the Ottawa Citizen and other outlets removed in September 2026; "
     "he communicated only by email and refused a video call.",
     "https://www.cbc.ca/news/canada/daniel-robson-suspected-fake-ai-persona-9.7363967"),
    ("Ervin B. Hoskins", "invented", BOGUS_BYLINES, OPENAI_2026),
    ("Noah Lamington", "invented", BOGUS_BYLINES, OPENAI_2026),
    ("Sophia Gonzalez", "invented", BOGUS_BYLINES, OPENAI_2026),
    ("Michael Harrison", "invented", BOGUS_BYLINES, OPENAI_2026),
    ("Ericka Feusier", "invented", BOGUS_BYLINES, OPENAI_2026),
    ("Jenny Williams", "invented", BOGUS_BYLINES, OPENAI_2026),
    ("Alice Johnson", "invented", BOGUS_BYLINES, OPENAI_2026),
    ("Geneviève Tremblay", "invented", WE_NEWS, WE_NEWS_SOURCE),
    ("Gordon Halloway", "invented", WE_NEWS, WE_NEWS_SOURCE),
    ("Caroline Williams", "impersonated",
     "a real science journalist. In 2026 an impostor used her name and clips to sell Science a "
     "story, which Science removed three months later, and then pitched Science and Knowable again.",
     "https://www.cjr.org/analysis/fake-caroline-williams-science-nature-magazine-ai-influx-pitches.php"),
    ("Katie Campbell", "impersonated",
     "a real KUOW reporter. In 2026 scammers used her name and Gmail addresses made to look like "
     "KUOW's to email book authors, then asked them to pay for interviews.",
     "https://kuow.org/technology/2026-10-12/scammers-used-ai-to-impersonate-me-a-kuow-reporter-heres-how-to-avoid-such-traps"),
]

# Webmail names that end like a web address (k.campbelkuow.org@gmail.com in
# the KUOW case) dress a free account up as an organisation's.
LOOKALIKE_LOCAL_RE = re.compile(r"[a-z0-9\-]+\.(?:com|org|net|edu|gov|news|media|co\.uk|org\.uk)$")

REMOVAL_PATTERNS = [
    r"\b(?:this|the)\s+(?:article|story|piece|essay|column|post)\s+(?:has\s+been|was)\s+"
    r"(?:removed|retracted|withdrawn|taken\s+down|deleted|unpublished)\b",
    r"\bit\s+has\s+been\s+(?:removed|retracted|withdrawn|taken\s+down)\b",
    r"\bwe\s+have\s+(?:removed|retracted|withdrawn|taken\s+down|unpublished)\b",
    r"\beditor[’']?s[’']?\s+note\b",
    r"\bnote\s+from\s+the\s+editors?\b",
    r"\bdid\s+not\s+meet\s+[\w'’ ]{0,40}standards\b",
    r"\b(?:could\s+not|unable\s+to|cannot)\s+(?:verify|confirm)\s+(?:the\s+)?(?:identity|author|writer)\b",
    r"\bimpersonat\w*",
]

# Bot-check pages some news sites send to scripts instead of the story. They
# load with HTTP 200, so without this they would read as a clip with no byline.
CHALLENGE_TITLE_RE = re.compile(
    r"<title[^>]*>\s*(?:just a moment|attention required|access denied|pardon our interruption|"
    r"are you a robot|robot check|security check|please verify you are a human|verify you are human|"
    r"one more step|request blocked|forbidden)\s*[.!?…]*\s*(?:\|[^<]*)?</title>",
    re.IGNORECASE)
CHALLENGE_MARKERS = ("captcha-delivery.com", "px-captcha", "_incapsula_resource", "_cf_chl_opt")

BLOCK_TAGS = frozenset({
    "p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "article", "header", "footer", "blockquote", "tr", "td",
    "figcaption", "title",
})
BYLINE_META = frozenset({
    "author", "article:author", "parsely-author", "sailthru.author", "byl",
    "dc.creator", "dcterms.creator", "citation_author", "cxenseparse:author",
})
SECOND_LEVEL = frozenset({
    "co", "com", "org", "net", "ac", "gov", "edu", "ltd", "plc", "me", "nhs",
    "sch", "or", "ne", "go", "nic",
})
NOT_EMAIL_TLDS = frozenset({"png", "jpg", "jpeg", "gif", "webp", "svg", "css", "js"})

URL_RE = re.compile(r"https?://[^\s<>\"'()\[\]]+")
URL_ONLY_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+\-]+@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)\b")
MAILTO_RE = re.compile(r"mailto:([^\"'?>\s]+)", re.IGNORECASE)
CFEMAIL_RE = re.compile(r"(?:data-cfemail=[\"']|/cdn-cgi/l/email-protection#)([0-9a-fA-F]{4,})")
QUOTE_RE = re.compile(r"[\"“](?=[^\s\"“”])([^\"“”]{40,700})(?<=\S)[\"”]")
EML_START_RE = re.compile(
    r"\A(?:Return-Path|Received|Delivered-To|From|MIME-Version|Message-ID|ARC-Seal|X-[\w-]+):",
    re.IGNORECASE)

_TOKEN = r"[A-Z][\w'’\-]+"
_NAME = r"%s(?:[ \t]+(?:[A-Z]\.|%s)){1,3}" % (_TOKEN, _TOKEN)
_TITLE = r"(?:(?:Dr|Prof|Professor|Mr|Mrs|Ms|Sen|Rep|Gov|Judge)\.?\s+)?"
_SPEECH = r"(?:said|says|explained|explains|added|adds|noted|notes|told|recalled|recalls|argued|argues|wrote|writes)"
QUOTED_PEOPLE_RES = [
    re.compile(r"\b%s\s+%s(%s)" % (_SPEECH, _TITLE, _NAME)),
    re.compile(r"\baccording\s+to\s+%s(%s)" % (_TITLE, _NAME)),
    re.compile(r"\b(%s),\s+(?:a|an|the)\s+[^.;:\"“”\n]{3,120}?,\s+%s\b" % (_NAME, _SPEECH)),
    re.compile(r"\b(%s)\s+%s\b" % (_NAME, _SPEECH)),
]
NAME_STOP = frozenset("""
The A An This That These Those In On At For From By With But And Or So If When While After
Before As He She They It We I You His Her Their Our Its Mr Mrs Ms Dr Prof Professor Sen Rep
Gov Judge Last Next Then Now Still Yet Also Monday Tuesday Wednesday Thursday Friday Saturday
Sunday January February March April May June July August September October November December
""".split())


# --- text helpers -----------------------------------------------------------

def normalize_name(s):
    """Lowercase, strip accents and punctuation, collapse spaces."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s.casefold())
    return re.sub(r"\s+", " ", s).strip()


def name_matches(claimed, candidate):
    """True if every word of the claimed name appears in the candidate byline."""
    want = normalize_name(claimed).split()
    have = normalize_name(candidate).split()
    return bool(want) and bool(have) and all(tok in have for tok in want)


def name_in_text(name, text):
    norm = normalize_name(name)
    return bool(norm) and (" %s " % norm) in (" %s " % normalize_name(text))


def slug_name(url):
    """'jane doe' from an author-page URL such as https://example.com/profile/jane-doe/."""
    try:
        path = urllib.parse.urlparse(url).path.rstrip("/")
    except ValueError:
        return ""
    slug = re.sub(r"\.\w+$", "", path.rsplit("/", 1)[-1])
    return " ".join(w for w in re.split(r"[-_+.]+", slug) if w and not w.isdigit())


def slug_matches(claimed, url):
    """True if an author-page URL is named after the claimed writer."""
    slug = slug_name(url)
    if not slug:
        return False
    return name_matches(claimed, slug) or normalize_name(claimed).replace(" ", "") == normalize_name(slug).replace(" ", "")


def _snippet(text, start, end, width=80):
    a = max(0, start - width)
    b = min(len(text), end + width)
    s = " ".join(text[a:b].split())
    return ("…" if a > 0 else "") + s + ("…" if b < len(text) else "")


def _dedupe(items):
    out = []
    for item in items:
        item = " ".join((item or "").split())
        if item and item not in out:
            out.append(item)
    return out


def extract_urls(text):
    out = []
    for m in URL_RE.finditer(text or ""):
        url = m.group(0).rstrip(".,;:!?)»”’")
        if url not in out:
            out.append(url)
    return out


def extract_emails(text):
    return _dedupe(m.group(0).lower() for m in EMAIL_RE.finditer(text or "")
                   if m.group(1).rsplit(".", 1)[-1].lower() not in NOT_EMAIL_TLDS)


def registrable_domain(host):
    """example.com from www.blog.example.com; keeps two-part suffixes like co.uk."""
    host = (host or "").strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    labels = [label for label in host.split(".") if label]
    if len(labels) <= 2:
        return ".".join(labels)
    if len(labels[-1]) == 2 and labels[-2] in SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def host_matches(host, domain):
    host = (host or "").lower()
    return host == domain or host.endswith("." + domain)


def _host(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


# --- pitch, draft and page analysis -----------------------------------------

def red_flags(text):
    """Phrases in the pitch that match documented fake-freelancer patterns."""
    found = []
    for key, label, why, patterns in RED_FLAGS:
        for pattern in patterns:
            m = re.search(pattern, text or "", re.IGNORECASE)
            if m:
                found.append({"flag": key, "label": label, "match": _snippet(text, m.start(), m.end()), "why": why})
                break
    return found


def persona_matches(name):
    """Documented invented or impersonated bylines that match the name on the pitch."""
    if len(normalize_name(name).split()) < 2:
        return []
    return [{"name": p, "kind": kind, "what": what, "source": source}
            for p, kind, what, source in PERSONAS
            if name_matches(name, p) or name_matches(p, name)]


def lookalike_addresses(addresses):
    """Webmail addresses whose name part looks like a newsroom's or other organisation's domain."""
    out = []
    for address in addresses:
        local, _, domain = address.lower().rpartition("@")
        if not local or registrable_domain(domain) not in FREE_MAIL:
            continue
        hit = next((d for _, domains in OUTLETS for d in domains
                    if re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(d), local)), None)
        if not hit:
            m = LOOKALIKE_LOCAL_RE.search(local)
            hit = m.group(0) if m else None
        if hit:
            out.append({"address": address, "looks_like": hit})
    return out


def claimed_outlets(text):
    """Outlets named in the pitch, as (name, domains), one entry per outlet."""
    found, seen = [], set()
    for name, domains in OUTLETS:
        if domains in seen:
            continue
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(name), text or ""):
            found.append((name, domains))
            seen.add(domains)
    return found


def unbacked_outlets(outlets, clip_urls):
    """Names of claimed outlets that no supplied clip comes from."""
    hosts = [_host(u) for u in clip_urls]
    return [name for name, domains in outlets
            if not any(host_matches(h, d) for h in hosts for d in domains)]


def extract_quotes(text, min_words=8):
    out = []
    for m in QUOTE_RE.finditer(text or ""):
        quote = " ".join(m.group(1).split())
        if len(quote.split()) >= min_words and quote not in out:
            out.append(quote)
    return out


def search_links(quote, max_words=14):
    """Exact-phrase web searches, to see if a quote was lifted from earlier stories."""
    phrase = " ".join(quote.split()[:max_words]).strip(" ,.;:")
    q = urllib.parse.quote_plus('"%s"' % phrase)
    return {
        "google": "https://www.google.com/search?q=" + q,
        "bing": "https://www.bing.com/search?q=" + q,
        "duckduckgo": "https://duckduckgo.com/?q=" + q,
    }


def quoted_people(text, exclude="", limit=25):
    """Names that follow or precede attribution words (said, according to...)."""
    hits = []
    for pattern in QUOTED_PEOPLE_RES:
        for m in pattern.finditer(text or ""):
            tokens = m.group(1).split()
            while tokens and tokens[0].rstrip(".") in NAME_STOP:
                tokens.pop(0)
            if len(tokens) < 2:
                continue
            name = " ".join(tokens)
            if exclude and name_matches(exclude, name):
                continue
            hits.append((m.start(1), name))
    hits.sort()
    return _dedupe(name for _, name in hits)[:limit]


def removal_notices(text, limit=5):
    found = []
    for pattern in REMOVAL_PATTERNS:
        for m in re.finditer(pattern, text or "", re.IGNORECASE):
            snip = _snippet(text, m.start(), m.end())
            if snip not in found:
                found.append(snip)
            if len(found) >= limit:
                return found
    return found


def is_challenge_page(html):
    """True for a bot-check or block page served in place of the story."""
    head = (html or "")[:200_000]
    if CHALLENGE_TITLE_RE.search(head):
        return True
    low = head.lower()
    return len(html or "") < 100_000 and any(m in low for m in CHALLENGE_MARKERS)


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = []
        self.jsonld = []
        self.author_links = []
        self.title = ""
        self.parts = []
        self._skip = 0
        self._jsonld = None
        self._in_title = False
        self._author_link = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("itemprop") or "").lower()
            if key and a.get("content"):
                self.meta.append((key, a["content"].strip()))
        elif tag == "script":
            if a.get("type", "").strip().lower().startswith("application/ld+json"):
                self._jsonld = []
            else:
                self._skip += 1
        elif tag in ("style", "template"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a" and "author" in a.get("rel", "").lower().split():
            self._author_link = []
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "script":
            if self._jsonld is not None:
                self.jsonld.append("".join(self._jsonld))
                self._jsonld = None
            elif self._skip:
                self._skip -= 1
        elif tag in ("style", "template"):
            if self._skip:
                self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "a" and self._author_link is not None:
            self.author_links.append("".join(self._author_link))
            self._author_link = None
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._jsonld is not None:
            self._jsonld.append(data)
            return
        if self._skip:
            return
        if self._in_title:
            self.title += data
        if self._author_link is not None:
            self._author_link.append(data)
        self.parts.append(data)

    def text(self):
        lines = (" ".join(line.split()) for line in "".join(self.parts).split("\n"))
        return "\n".join(line for line in lines if line)


def _parse_html(html):
    p = _PageParser()
    try:
        p.feed(html or "")
        p.close()
    except Exception:  # html.parser rarely raises, but a page must never stop the run
        pass
    return p


def html_text(html):
    """Visible text of an HTML page or email, without scripts and styles."""
    return _parse_html(html).text()


def _load_jsonld(raw):
    """Parse one JSON-LD block, tolerating HTML comment or CDATA wrappers and raw newlines."""
    raw = re.sub(r"^\s*(?:<!--|//\s*<!\[CDATA\[)", "", raw or "")
    raw = re.sub(r"(?:-->|//\s*\]\]>)\s*$", "", raw)
    return json.loads(raw.strip(), strict=False)


def jsonld_authors(blocks):
    """Author and creator names in JSON-LD, following @id references (as Yoast writes them)."""
    docs = []
    for raw in blocks:
        try:
            docs.append(_load_jsonld(raw))
        except ValueError:
            continue
    ids = {}

    def index(node, depth=0):
        if depth > 12:
            return
        if isinstance(node, list):
            for item in node:
                index(item, depth + 1)
        elif isinstance(node, dict):
            if isinstance(node.get("@id"), str) and isinstance(node.get("name"), str):
                ids.setdefault(node["@id"], node["name"])
            for value in node.values():
                if isinstance(value, (list, dict)):
                    index(value, depth + 1)

    def names_of(value, depth=0):
        if depth > 6:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            out = []
            for item in value:
                out.extend(names_of(item, depth + 1))
            return out
        if isinstance(value, dict):
            name = value.get("name")
            if not name and isinstance(value.get("@id"), str):
                name = ids.get(value["@id"])
            if not name:
                name = value.get("url")
            return names_of(name, depth + 1) if name else []
        return []

    names = []

    def walk(node, depth=0):
        if depth > 12:
            return
        if isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
        elif isinstance(node, dict):
            for key in ("author", "creator"):
                if key in node:
                    names.extend(names_of(node[key]))
            for key, value in node.items():
                if key not in ("author", "creator") and isinstance(value, (list, dict)):
                    walk(value, depth + 1)

    for doc in docs:
        index(doc)
    for doc in docs:
        walk(doc)
    return names


def analyze_page(html, name):
    """Bylines, removal notices and quoted people on one published clip."""
    p = _parse_html(html)
    meta = [re.sub(r"^by\s+", "", v, flags=re.IGNORECASE) for k, v in p.meta if k in BYLINE_META]
    found = _dedupe(meta + jsonld_authors(p.jsonld) + p.author_links)
    bylines = [b for b in found if not URL_ONLY_RE.match(b)]
    author_urls = [b for b in found if URL_ONLY_RE.match(b)]
    text = p.text()
    return {
        "title": " ".join(p.title.split()),
        "bylines": bylines,
        "author_urls": author_urls,
        "byline_match": (any(name_matches(name, b) for b in bylines)
                         or any(slug_matches(name, u) for u in author_urls)),
        "name_on_page": name_in_text(name, text),
        "removal_notices": removal_notices(text),
        "people_quoted": quoted_people(text, exclude=name),
    }


# --- saved emails -----------------------------------------------------------

def looks_like_email(raw, path=""):
    return (path or "").lower().endswith(".eml") or bool(EML_START_RE.match((raw or "").lstrip()))


def parse_email(raw):
    """Body text and sender headers of a saved email (.eml)."""
    msg = email.message_from_string(raw or "", policy=policy.default)

    def addresses(header):
        values = [str(v) for v in (msg.get_all(header) or [])]
        return _dedupe(addr.lower() for _, addr in getaddresses(values) if "@" in addr)

    # Only the top Authentication-Results header was added by the editor's own
    # mail server; lower ones can be written by whoever sent the message.
    auth = {}
    headers = msg.get_all("Authentication-Results") or []
    if headers:
        for mech, result in re.findall(r"\b(spf|dkim|dmarc)=([a-z]+)", str(headers[0]), re.IGNORECASE):
            auth.setdefault(mech.lower(), result.lower())
    text = ""
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is not None:
        try:
            text = body.get_content()
        except (LookupError, ValueError, KeyError, AttributeError):  # unknown charset or broken encoding
            payload = body.get_payload(decode=True) or b""
            text = payload.decode("utf-8", errors="replace")
        if body.get_content_type() == "text/html":
            text = html_text(text)
    subject = " ".join(str(msg.get("Subject") or "").split())
    return {
        "from": addresses("From"),
        "reply_to": addresses("Reply-To"),
        "auth": auth,
        "subject": subject,
        "text": (subject + "\n\n" + (text or "")).strip(),
    }


def sender_notes(sender):
    """What the headers of a saved pitch email say about who sent it."""
    notes = []
    if not sender:
        return notes
    other = [a for a in sender["reply_to"] if a not in sender["from"]]
    if other:
        notes.append("**Check:** replies go to %s, not the sending address (%s). Reply to an address "
                     "you have confirmed yourself." % (", ".join(other), ", ".join(sender["from"]) or "none"))
    failed = ["%s=%s" % (m.upper(), r) for m, r in sorted(sender["auth"].items())
              if r in ("fail", "softfail", "permerror")]
    if failed:
        notes.append("**Check:** your mail server recorded %s for this message, so the sender may not "
                     "control the address it came from." % ", ".join(failed))
    return notes


# --- the writer's own site --------------------------------------------------

def site_pages(site):
    """The site as given, plus /contact and /about when only a domain was given."""
    url = site if "://" in site else "https://" + site
    parts = urllib.parse.urlparse(url)
    pages = [url]
    if not parts.path.strip("/"):
        base = "%s://%s" % (parts.scheme, parts.netloc)
        pages += [base + "/contact", base + "/about"]
    return pages


def decode_cfemail(hexstr):
    """An address hidden by Cloudflare's email obfuscation (common on personal sites)."""
    key = int(hexstr[:2], 16)
    return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr) - 1, 2))


def page_emails(html):
    found = [urllib.parse.unquote(m.group(1)) for m in MAILTO_RE.finditer(html or "")]
    found += [decode_cfemail(m.group(1)) for m in CFEMAIL_RE.finditer(html or "")]
    found += extract_emails(html_text(html))
    return _dedupe(e.strip().lower() for e in found if extract_emails(e.strip()) == [e.strip().lower()])


def check_site_contacts(site, fetch_fn):
    res = {"site": site, "pages_read": [], "emails": [], "error": None}
    pages = site_pages(site)
    for url in pages:
        reply = fetch_fn(url)
        if reply.get("text") and not is_challenge_page(reply["text"]):
            res["pages_read"].append(url)
            for e in page_emails(reply["text"]):
                if e not in res["emails"]:
                    res["emails"].append(e)
        elif url == pages[0]:
            res["error"] = reply.get("error") or ("bot check page" if reply.get("text") else "no reply")
    return res


def compare_contacts(pitch_addresses, site_emails):
    """'match', 'mismatch' or 'none_listed'; None when there is nothing to compare."""
    if not pitch_addresses or site_emails is None:
        return None
    if not site_emails:
        return "none_listed"
    return "match" if set(pitch_addresses) & set(site_emails) else "mismatch"


# --- network checks ---------------------------------------------------------

def fetch(url, timeout=TIMEOUT):
    """GET a URL; returns {"status", "url", "text", "error"} and never raises."""
    if not url.lower().startswith(("http://", "https://")):
        return {"status": None, "url": url, "text": None, "error": "not an http(s) URL"}
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.5",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(MAX_BYTES)
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                text = raw.decode(charset, errors="replace")
            except LookupError:
                text = raw.decode("utf-8", errors="replace")
            return {"status": resp.status, "url": resp.geturl(), "text": text, "error": None}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "url": url, "text": None, "error": "HTTP %d" % e.code}
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as e:
        return {"status": None, "url": url, "text": None, "error": str(getattr(e, "reason", e))}


def wayback_api(url):
    """CDX query for the earliest Wayback Machine capture of a URL."""
    return CDX_URL + urllib.parse.urlencode(
        {"url": url, "output": "json", "limit": "1", "fl": "timestamp,original"})


def wayback_latest_api(url):
    """CDX query for the latest capture that loaded normally (HTTP 200)."""
    return CDX_URL + urllib.parse.urlencode(
        {"url": url, "output": "json", "limit": "-1", "fl": "timestamp,original",
         "filter": "statuscode:200"})


def archived_copy_url(timestamp, original):
    """The original HTML of one Wayback Machine capture (id_ skips the archive's toolbar)."""
    return "https://web.archive.org/web/%sid_/%s" % (timestamp, original)


def parse_cdx_row(text):
    """(timestamp, original URL) of the first capture in a CDX JSON reply."""
    text = (text or "").strip()
    if not text:
        return None
    rows = json.loads(text)
    if len(rows) < 2 or len(rows[1]) < 2:
        return None
    ts, original = str(rows[1][0]), str(rows[1][1])
    if len(ts) < 8 or not ts.isdigit():
        return None
    return ts, original


def _ts_date(ts):
    return "%s-%s-%s" % (ts[:4], ts[4:6], ts[6:8])


def parse_cdx(text):
    """Capture date (YYYY-MM-DD) of the first row of a CDX JSON reply."""
    row = parse_cdx_row(text)
    return _ts_date(row[0]) if row else None


def parse_rdap(text):
    """Registration date (YYYY-MM-DD) from an RDAP domain reply."""
    data = json.loads(text)
    for event in data.get("events", []) if isinstance(data, dict) else []:
        if event.get("eventAction") == "registration" and event.get("eventDate"):
            return str(event["eventDate"])[:10]
    return None


def _first_archived(target, fetch_fn, res):
    reply = fetch_fn(wayback_api(target))
    if reply.get("text") is None:
        res["archive_error"] = reply.get("error") or "no reply"
        return
    try:
        res["first_archived"] = parse_cdx(reply["text"])
    except (ValueError, TypeError, KeyError, IndexError):
        res["archive_error"] = "unreadable Wayback Machine reply"


def _latest_capture(url, fetch_fn):
    reply = fetch_fn(wayback_latest_api(url))
    try:
        return parse_cdx_row(reply.get("text"))
    except (ValueError, TypeError, KeyError, IndexError):
        return None


def _redirected_home(url, final_url):
    if not final_url or final_url == url:
        return False
    before = urllib.parse.urlparse(url).path.strip("/")
    after = urllib.parse.urlparse(final_url).path.strip("/")
    return bool(before) and not after


def check_clip(url, name, fetch_fn):
    """Check one claimed clip. If the live page can't be read (refused, a bot
    check, removed or redirected to the home page), read the Wayback Machine's
    latest normal capture instead."""
    res = {"url": url, "status": None, "final_url": None, "error": None, "redirected_home": False,
           "blocked": False, "read_from": None, "archived_on": None, "title": "", "bylines": [],
           "author_urls": [], "byline_match": False, "name_on_page": False, "removal_notices": [],
           "people_quoted": [], "first_archived": None, "archive_error": None}
    reply = fetch_fn(url)
    res["status"], res["final_url"], res["error"] = reply.get("status"), reply.get("url"), reply.get("error")
    res["redirected_home"] = _redirected_home(url, reply.get("url"))
    html = reply.get("text")
    if html and is_challenge_page(html):
        res["blocked"] = True
    elif html and not res["redirected_home"]:
        res.update(analyze_page(html, name))
        res["read_from"] = "live"
    _first_archived(url, fetch_fn, res)
    if res["read_from"] is None and res["first_archived"]:
        capture = _latest_capture(url, fetch_fn)
        if capture:
            archived = fetch_fn(archived_copy_url(*capture))
            if archived.get("text") and not is_challenge_page(archived["text"]):
                res.update(analyze_page(archived["text"], name))
                res["read_from"] = "wayback"
                res["archived_on"] = _ts_date(capture[0])
    return res


def check_domain(domain, fetch_fn, today):
    res = {"domain": domain, "registered": None, "age_days": None, "new": False,
           "first_archived": None, "archive_error": None, "notes": []}
    reply = fetch_fn(RDAP_URL + domain)
    if reply.get("text"):
        try:
            res["registered"] = parse_rdap(reply["text"])
        except (ValueError, AttributeError, TypeError):
            res["notes"].append("RDAP reply unreadable")
    else:
        res["notes"].append("RDAP: %s" % (reply.get("error") or "no reply"))
    if res["registered"]:
        try:
            res["age_days"] = (today - date.fromisoformat(res["registered"])).days
            res["new"] = res["age_days"] < NEW_DOMAIN_DAYS
        except ValueError:
            pass
    _first_archived(domain, fetch_fn, res)
    return res


# --- report -----------------------------------------------------------------

HUMAN_STEPS = [
    "Talk to the writer live, on video or by phone, before you commission, and ask about the "
    "reporting behind the pitch. On a voice call Undark found that a writer did not know the "
    "material in her own pitch. After the fake 'Daniel Robson' case the Ottawa Citizen now asks "
    "new opinion writers to meet a staff journalist in person and pose for a photo.",
    "Confirm the pitch comes from the person whose name and clips it uses. A matching byline only "
    "shows the clips exist: in 2026 someone posing as an established science journalist sold Science "
    "a story under her name. Reach the writer through contact details on their own website or an "
    "earlier exchange you trust, not through the pitch.",
    "Pay only through your normal payments system, with verified identity details. That step "
    "is what exposed 'Margaux Blanchard' at WIRED.",
    "Contact people quoted in the writer's earlier clips, using contact details you find "
    "yourself, and ask whether they spoke to the writer. That is how The Local's editor found "
    "sources who had never spoken to a freelancer he was checking.",
    "Confirm earlier bylines with editors at those outlets, reached through the outlet's own "
    "masthead or switchboard, not through contacts supplied in the pitch, and ask how they "
    "verified the writer. Earlier bylines are not a reference on their own: the 'Bogus Bylines' "
    "personas cited their earlier placements as credentials, and one newspaper ran a syndicated "
    "column because it trusted the syndicator.",
    "Ask for an annotated draft or the document's version history. The Local now asks authors "
    "for annotated drafts, and some freelancers offer editors their Google Docs history.",
    "Before publishing, confirm every quote with the person quoted. Science removed a story "
    "after two of its quotes turned out to come from other writers' published stories.",
    "Do not rely on AI-text detectors: two of them rated the fabricated WIRED feature as "
    "likely human-written.",
]


def run_checks(name, pitch="", draft="", clips=(), sites=(), fetch_fn=None, today=None, sender=None):
    """Build the full report. fetch_fn=None means offline: text checks only.
    sender is parse_email()'s result when the pitch is a saved email."""
    today = today or date.today()
    pitch, draft = pitch or "", draft or ""
    clip_urls = []
    for url in list(clips) + extract_urls(pitch):
        if url not in clip_urls:
            clip_urls.append(url)
    # From a saved email, trust the headers; in pasted text, quoted replies
    # can carry other people's addresses, but every address is still listed.
    pitch_addresses = _dedupe(sender["from"] + sender["reply_to"]) if sender else extract_emails(pitch)
    domains, free_mail = [], []
    for site in sites:
        d = registrable_domain(_host(site if "://" in site else "http://" + site))
        if d and d not in domains:
            domains.append(d)
    for address in pitch_addresses:
        d = registrable_domain(address.rsplit("@", 1)[-1])
        if d in FREE_MAIL:
            if d not in free_mail:
                free_mail.append(d)
        elif d and d not in domains:
            domains.append(d)
    report = {
        "tool": "byline-check",
        "version": __version__,
        "name": name,
        "checked_on": today.isoformat(),
        "offline": fetch_fn is None,
        "persona_matches": persona_matches(name),
        "sender": sender and {k: sender[k] for k in ("from", "reply_to", "auth", "subject")},
        "sender_notes": sender_notes(sender),
        "pitch_addresses": pitch_addresses,
        "lookalike_addresses": lookalike_addresses(pitch_addresses),
        "pitch_flags": red_flags(pitch),
        "claimed_outlets_without_clips": unbacked_outlets(claimed_outlets(pitch), clip_urls),
        "free_mail_domains": free_mail,
        "draft_quotes": [{"quote": q, "search": search_links(q)} for q in extract_quotes(draft)],
        "draft_people_quoted": quoted_people(draft, exclude=name),
        "clip_urls": clip_urls,
        "clips": [],
        "domains_to_check": domains,
        "domains": [],
        "sites": list(sites),
        "site_contacts": [],
        "contact_match": None,
        "human_steps": HUMAN_STEPS,
    }
    if fetch_fn is not None:
        report["clips"] = [check_clip(u, name, fetch_fn) for u in clip_urls[:MAX_CLIPS]]
        report["domains"] = [check_domain(d, fetch_fn, today) for d in domains[:MAX_DOMAINS]]
        report["site_contacts"] = [check_site_contacts(s, fetch_fn) for s in list(sites)[:MAX_SITES]]
        if report["site_contacts"]:
            site_emails = _dedupe(e for s in report["site_contacts"] for e in s["emails"])
            report["contact_match"] = compare_contacts(pitch_addresses, site_emails)
    return report


def _persona_lines(r):
    lines = []
    for p in r["persona_matches"]:
        if p["kind"] == "impersonated":
            lines.append("- **Check:** %s is the name of %s Unless this is a namesake, reach the writer "
                         "through contact details you find yourself and ask them to confirm this pitch. "
                         "Source: %s"
                         % (p["name"], p["what"], p["source"]))
        else:
            lines.append("- **Check:** %s was the byline of %s Real people share names, so this proves "
                         "nothing alone; confirm who you are dealing with on a live call. Source: %s"
                         % (p["name"], p["what"], p["source"]))
    return lines


def _lookalike_lines(r):
    return ["- **Check:** %s is a free webmail address whose name part looks like a web address (%s). "
            "In 2026 scammers posing as a KUOW reporter wrote from k.campbelkuow.org@gmail.com. "
            "Confirm with that organisation, through contact details you find yourself, that the "
            "sender works there." % (a["address"], a["looks_like"])
            for a in r["lookalike_addresses"]]


def _clip_lines(c):
    lines = ["### %s" % c["url"]]
    if c["status"] in (404, 410):
        lines.append("- **Check:** HTTP %d, page not found: the story may have been removed, "
                     "or the link is wrong" % c["status"])
    elif c["status"] is None:
        lines.append("- **Could not load:** %s" % (c["error"] or "no reply"))
    elif c["error"]:
        lines.append("- **Could not load:** %s (some sites block scripts; open it in a browser)" % c["error"])
    elif c["blocked"]:
        lines.append("- **Could not read:** the site sent a bot check page instead of the story; "
                     "open it in a browser")
    else:
        lines.append("- Loaded: HTTP %s%s" % (c["status"], "" if c["final_url"] in (None, c["url"])
                                                else ", ended at %s" % c["final_url"]))
    if c["redirected_home"]:
        lines.append("- **Check:** the link now goes to the site's home page; the story may have been removed.")
    if c["read_from"] == "wayback":
        lines.append("- Read from the Wayback Machine's copy of %s instead, so a later removal "
                     "would not show here" % c["archived_on"])
    if c["title"]:
        lines.append("- Title: %s" % c["title"])
    if c["read_from"]:
        if c["byline_match"]:
            lines.append("- Byline in page data: yes (%s)" % "; ".join(c["bylines"] + c["author_urls"]))
        elif c["bylines"]:
            lines.append("- **Check:** byline in page data is %s, not the name in the pitch" % "; ".join(c["bylines"]))
        elif c["name_on_page"]:
            lines.append("- No byline in page data; the name does appear in the page text")
        else:
            lines.append("- **Check:** no byline found and the name is not in the page text")
        if c["author_urls"] and not c["byline_match"]:
            lines.append("- Author links in page data: %s" % "; ".join(c["author_urls"]))
    for notice in c["removal_notices"]:
        lines.append("- **Possible notice (read it):** %s" % notice)
    if c["first_archived"]:
        lines.append("- First saved by the Wayback Machine: %s" % c["first_archived"])
    elif c["archive_error"]:
        lines.append("- Wayback Machine: %s" % c["archive_error"])
    else:
        lines.append("- Wayback Machine: never saved")
    if c["people_quoted"]:
        lines.append("- People or organisations quoted (contact them yourself): %s" % ", ".join(c["people_quoted"]))
    return lines


def _contact_lines(r):
    lines = []
    for s in r["site_contacts"]:
        if s["error"] and not s["pages_read"]:
            lines.append("- %s: could not read the site (%s)" % (s["site"], s["error"]))
        elif s["emails"]:
            lines.append("- %s lists: %s" % (s["site"], ", ".join(s["emails"])))
        else:
            lines.append("- %s: no email address found on %d page(s) read" % (s["site"], len(s["pages_read"])))
    sent = ", ".join(r["pitch_addresses"])
    listed = _dedupe(e for s in r["site_contacts"] for e in s["emails"])
    if r["contact_match"] == "match":
        lines.append("- The pitch's address is listed on the writer's own site.")
    elif r["contact_match"] == "mismatch":
        lines.append("- **Check:** the pitch came from %s, but the writer's own site lists %s. In 2026 "
                     "someone posing as an established science journalist sold Science a story under "
                     "her name. Write to the address on the site and ask the writer to confirm the pitch."
                     % (sent, ", ".join(listed)))
    elif r["contact_match"] == "none_listed":
        lines.append("- The site lists no address to compare with the pitch's (%s). Find the writer's "
                     "contact details yourself and ask them to confirm the pitch." % sent)
    return lines


def render_markdown(r):
    out = [
        "# Pitch verification worksheet: %s" % r["name"],
        "",
        "Checked %s with byline-check %s. This sheet lists evidence to look at. "
        "It does not say whether the writer is real, and it does no AI-text detection." % (r["checked_on"], r["version"]),
        "",
        "## 1. Pitch and correspondence",
    ]
    out += _persona_lines(r)
    if r["sender"]:
        out.append("- Sent from: %s" % (", ".join(r["sender"]["from"]) or "no From address"))
        out += ["- " + note for note in r["sender_notes"]]
    out += _lookalike_lines(r)
    if r["pitch_flags"]:
        for f in r["pitch_flags"]:
            out.append("- **%s:** \"%s\". %s" % (f["label"], f["match"], f["why"]))
    else:
        out.append("- No email-only or payment phrases found.")
    if r["claimed_outlets_without_clips"]:
        out.append("- **Check:** outlets named in the pitch with no clip supplied from them: %s"
                   % ", ".join(r["claimed_outlets_without_clips"]))
    if r["free_mail_domains"]:
        out.append("- Free webmail (%s): no domain to check. Common among real freelancers too."
                   % ", ".join(r["free_mail_domains"]))
    out += ["", "## 2. Claimed clips"]
    if not r["clip_urls"]:
        out.append("- No clip links given. Ask for links to published work.")
    elif r["offline"]:
        out += ["- Not fetched (offline): %s" % u for u in r["clip_urls"]]
    else:
        for c in r["clips"]:
            out += _clip_lines(c) + [""]
        if len(r["clip_urls"]) > len(r["clips"]):
            out.append("- %d more links not checked." % (len(r["clip_urls"]) - len(r["clips"])))
    out += ["", "## 3. Writer's own site and domains"]
    if not r["domains_to_check"]:
        out.append("- None given (use --site for the writer's website).")
    elif r["offline"]:
        out += ["- Not checked (offline): %s" % d for d in r["domains_to_check"]]
    for d in r["domains"]:
        line = "- %s: " % d["domain"]
        if d["registered"]:
            line += "registered %s (%s days ago)" % (d["registered"], d["age_days"])
            if d["new"]:
                line += " **less than a year old**"
        else:
            line += "registration date unknown"
        line += "; first saved by the Wayback Machine: %s" % (d["first_archived"] or d["archive_error"] or "never")
        if d["notes"]:
            line += " (%s)" % "; ".join(d["notes"])
        out.append(line)
    out += _contact_lines(r)
    out += ["", "## 4. Quotes in the draft"]
    if r["draft_quotes"]:
        out.append("Search each quote as an exact phrase to see whether it was published before:")
        for i, q in enumerate(r["draft_quotes"], 1):
            s = q["search"]
            short = q["quote"] if len(q["quote"]) <= 160 else q["quote"][:157] + "..."
            out.append("%d. \"%s\" [Google](%s) · [Bing](%s) · [DuckDuckGo](%s)"
                       % (i, short, s["google"], s["bing"], s["duckduckgo"]))
    else:
        out.append("- No long direct quotes found (or no draft given).")
    if r["draft_people_quoted"]:
        out.append("- Sources named in the draft (confirm each one): %s" % ", ".join(r["draft_people_quoted"]))
    out += ["", "## 5. Still to do by a person"]
    out += ["%d. %s" % (i, step) for i, step in enumerate(r["human_steps"], 1)]
    return "\n".join(out)


def _read(path):
    if not path:
        return ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="byline-check",
        description="Verification worksheet for an editor vetting a freelance pitch.")
    ap.add_argument("--name", required=True, help="the byline the writer uses")
    ap.add_argument("--pitch", help="the pitch and any correspondence: a text file, or a saved email (.eml)")
    ap.add_argument("--draft", help="text file with the submitted draft")
    ap.add_argument("--clip", action="append", default=[],
                    help="URL of a story the writer says they published (repeatable)")
    ap.add_argument("--site", action="append", default=[],
                    help="the writer's own website or email domain (repeatable)")
    ap.add_argument("--offline", action="store_true", help="check the text only; fetch nothing")
    ap.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    ap.add_argument("--out", help="write the worksheet to this file (UTF-8) instead of stdout")
    ap.add_argument("--version", action="version", version="byline-check " + __version__)
    args = ap.parse_args(argv)
    pitch, sender = _read(args.pitch), None
    if args.pitch and looks_like_email(pitch, args.pitch):
        sender = parse_email(pitch)
        pitch = sender["text"]
    report = run_checks(args.name, pitch, _read(args.draft), args.clip, args.site,
                        None if args.offline else fetch, sender=sender)
    text = json.dumps(report, indent=2, ensure_ascii=False) if args.json else render_markdown(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
