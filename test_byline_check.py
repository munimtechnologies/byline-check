import json
import os
import re
import sys
import tempfile
import unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import byline_check as bc  # noqa: E402

DATASET = os.path.join(HERE, "personas.json")

ARTICLE = """<!DOCTYPE html><html><head><title>Minecraft weddings</title>
<meta name="author" content="Jane Q. Doe">
<meta property="og:title" content="Not a byline">
<script type="application/ld+json">{"@context": "https://schema.org", "@graph": [{"@type": "NewsArticle",
"headline": "x", "author": [{"@type": "Person", "name": "Jane Q. Doe"}, {"@type": "Person", "name": "Sam Roe"}]}]}</script>
<script>var x = "said Fake Person";</script>
<style>.a { color: red }</style>
</head><body><article>
<p>By <a rel="author" href="/by/jane">Jane Q. Doe</a></p>
<p>&ldquo;It felt like a real ceremony,&rdquo; said Dr. Alex Moreno, a sociologist.</p>
<p>Priya Shah, a game designer in Austin, said the trend was growing.</p>
<p>On Tuesday Lee Park said nothing.</p>
<p>The Senate said it would vote.</p>
</article></body></html>
"""

# Yoast-style graph: the article's author is only an @id reference, a headline
# carries a raw newline, and article:author is a Facebook page URL.
YOAST = """<html><head><title>Story</title>
<meta property="article:author" content="https://www.facebook.com/examplemag">
<script type="application/ld+json" class="yoast-schema-graph">{"@context":"https://schema.org","@graph":[
{"@type":"Article","@id":"https://ex.example/s/#article","author":{"@id":"https://ex.example/#/schema/person/abc"},
"headline":"Line one
line two"},
{"@type":"Person","@id":"https://ex.example/#/schema/person/abc","name":"Jane Doe"}]}</script>
</head><body><p>Text</p></body></html>"""

PROFILE = ('<html><head><meta property="article:author" content="https://www.example-news.com/profile/jane-doe">'
           '</head><body>Story</body></html>')

CHALLENGE = "<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>"

REMOVED = """<html><head><meta name="byl" content="By Margo Example"></head><body>
<p>Editor&rsquo;s note: This article has been removed after we determined the author was
impersonating an established journalist.</p></body></html>"""

# A clip under a documented persona's byline, and one whose only author data
# is an author-page URL named after a persona.
PERSONA_PAGE = """<html><head><title>Op-ed</title><meta name="author" content="Alice Johnson"></head>
<body><p>&ldquo;Blue walls calm anxious dogs within days,&rdquo; said Dr Eleni Nicolaou, an art therapist.</p>
</body></html>"""
PERSONA_AUTHOR_URL = ('<html><head><meta property="article:author" '
                      'content="https://www.middleeastmonitor.com/authors/ervin-hoskins/"></head>'
                      '<body>Column</body></html>')

PITCH = """Hi, I'm Jane Doe, a freelancer who has written for WIRED and Business Insider.
Clips: https://www.wired.com/story/minecraft-weddings/ and https://janedoe.example/about.
I'm travelling, so I can only communicate by email for now. Could you pay me via PayPal?
jane.doe@gmail.com"""

DRAFT = """Couples now marry inside games. "We wanted our friends from every continent to be there with us," said Maria Lopez, who married in March.
"Short one," she said."""

EXPERT_DRAFT = """Pet owners are repainting. "A soft blue wall can lower your dog's stress in a matter of days," said Dr. Eleni Nicolaou, an art therapist.
Maria Lopez said she tried it."""

EML = """Return-Path: <bounce@mailer.example>
Authentication-Results: mx.newsroom.example; spf=softfail smtp.mailfrom=mailer.example; dkim=none; dmarc=fail header.from=janedoe.example
Authentication-Results: forged.example; spf=pass; dkim=pass; dmarc=pass
From: Jane Doe <jane@janedoe.example>
Reply-To: Jane Doe <jane.doe.writer@gmail.com>
To: editor@newsroom.example
Subject: Pitch: Minecraft weddings
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"

Hi, I'm travelling, so I can only communicate by email for now.
"""

EML_HTML = """From: Sam Roe <sam@roe.example>
Content-Type: text/html; charset="utf-8"

<p>Could you pay me via <b>PayPal</b>?</p><script>var hidden = 1;</script>
"""

SITE_HTML = '<html><body><a href="mailto:jane@janedoe.example">Email me</a></body></html>'

CLIP = "https://www.wired.com/story/minecraft-weddings/"
CDX_REPLY = '[["timestamp","original"],["20190405123456","https://www.wired.com/story/minecraft-weddings/"]]'
LATEST_REPLY = '[["timestamp","original"],["20260901000000","https://www.wired.com/story/minecraft-weddings/"]]'
RDAP_REPLY = json.dumps({"events": [
    {"eventAction": "last changed", "eventDate": "2026-09-01T00:00:00Z"},
    {"eventAction": "registration", "eventDate": "2026-08-01T12:00:00Z"},
]})


def ok(url, text):
    return {"status": 200, "url": url, "text": text, "error": None}


def fake_fetch(pages):
    def _fetch(url):
        if url in pages:
            return pages[url]
        return {"status": 404, "url": url, "text": None, "error": "HTTP 404"}
    return _fetch


def archived(live_reply, page_text):
    """Pages for a clip whose live reply is live_reply and whose latest capture is page_text."""
    return {
        CLIP: live_reply,
        bc.wayback_api(CLIP): ok(bc.wayback_api(CLIP), CDX_REPLY),
        bc.wayback_latest_api(CLIP): ok(bc.wayback_latest_api(CLIP), LATEST_REPLY),
        bc.archived_copy_url("20260901000000", CLIP): ok("", page_text),
    }


def cf_encode(address, key=0x5A):
    return "%02x" % key + "".join("%02x" % (ord(c) ^ key) for c in address)


class NameTests(unittest.TestCase):
    def test_middle_initial_matches(self):
        self.assertTrue(bc.name_matches("Jane Doe", "Jane Q. Doe"))

    def test_different_first_name(self):
        self.assertFalse(bc.name_matches("Jane Doe", "John Doe"))

    def test_accents_ignored(self):
        self.assertTrue(bc.name_matches("José Núñez", "Jose Nunez"))

    def test_empty(self):
        self.assertFalse(bc.name_matches("", "Jane Doe"))
        self.assertFalse(bc.name_matches("Jane Doe", ""))

    def test_name_in_text(self):
        self.assertTrue(bc.name_in_text("Jane Doe", "Story by JANE DOE, staff"))
        self.assertFalse(bc.name_in_text("Jane Doe", "Story by Janet Doerr"))

    def test_slug_name(self):
        self.assertEqual(bc.slug_name("https://www.example.com/profile/jane-doe/"), "jane doe")
        self.assertEqual(bc.slug_name("https://ex.example/author/jane_doe.html"), "jane doe")
        self.assertEqual(bc.slug_name("https://ex.example/"), "")

    def test_slug_matches(self):
        self.assertTrue(bc.slug_matches("Jane Doe", "https://www.example.com/profile/jane-doe"))
        self.assertTrue(bc.slug_matches("Jane Doe", "https://social.example/janedoe"))
        self.assertFalse(bc.slug_matches("Jane Doe", "https://www.facebook.com/examplemag"))
        self.assertFalse(bc.slug_matches("Jane Doe", "https://www.facebook.com/"))


class PageTests(unittest.TestCase):
    def setUp(self):
        self.page = bc.analyze_page(ARTICLE, "Jane Doe")

    def test_title(self):
        self.assertEqual(self.page["title"], "Minecraft weddings")

    def test_bylines_from_meta_jsonld_and_rel_author(self):
        self.assertEqual(set(self.page["bylines"]), {"Jane Q. Doe", "Sam Roe"})
        self.assertEqual(self.page["author_urls"], [])
        self.assertTrue(self.page["byline_match"])

    def test_people_quoted(self):
        self.assertEqual(self.page["people_quoted"], ["Alex Moreno", "Priya Shah", "Lee Park"])

    def test_no_persona_or_fake_expert(self):
        self.assertEqual(self.page["persona_bylines"], [])
        self.assertEqual(self.page["fake_experts_quoted"], [])

    def test_scripts_are_not_text(self):
        self.assertNotIn("Fake Person", self.page["people_quoted"])

    def test_no_removal_notice(self):
        self.assertEqual(self.page["removal_notices"], [])

    def test_removed_story(self):
        page = bc.analyze_page(REMOVED, "Jane Doe")
        self.assertEqual(page["bylines"], ["Margo Example"])
        self.assertFalse(page["byline_match"])
        self.assertTrue(page["removal_notices"])
        self.assertIn("has been removed", page["removal_notices"][0])

    def test_ordinary_withdrawal_is_not_a_notice(self):
        self.assertEqual(bc.removal_notices("A bill that was withdrawn last year."), [])

    def test_broken_jsonld_is_skipped(self):
        self.assertEqual(bc.jsonld_authors(["{not json", '{"author": "A. Writer"}']), ["A. Writer"])

    def test_jsonld_in_comment(self):
        self.assertEqual(bc.jsonld_authors(['<!--{"author": {"name": "A. Writer"}}-->']), ["A. Writer"])

    def test_yoast_id_reference_and_url_author(self):
        page = bc.analyze_page(YOAST, "Jane Doe")
        self.assertEqual(page["bylines"], ["Jane Doe"])
        self.assertEqual(page["author_urls"], ["https://www.facebook.com/examplemag"])
        self.assertTrue(page["byline_match"])
        self.assertEqual(page["persona_bylines"], [])

    def test_author_page_url_matches(self):
        page = bc.analyze_page(PROFILE, "Jane Doe")
        self.assertEqual(page["bylines"], [])
        self.assertTrue(page["byline_match"])
        self.assertFalse(bc.analyze_page(PROFILE, "John Smith")["byline_match"])

    def test_challenge_pages(self):
        self.assertTrue(bc.is_challenge_page(CHALLENGE))
        self.assertTrue(bc.is_challenge_page("<title>Attention Required! | Cloudflare</title>"))
        self.assertFalse(bc.is_challenge_page(ARTICLE))
        self.assertFalse(bc.is_challenge_page("<title>Access denied: inside the fight over library cards</title>"))


class PitchTests(unittest.TestCase):
    def test_red_flags(self):
        flags = bc.red_flags(PITCH)
        self.assertEqual([f["flag"] for f in flags], ["email-only", "payment"])
        self.assertIn("only communicate by email", flags[0]["match"])
        self.assertIn("PayPal", flags[1]["match"])

    def test_no_red_flags(self):
        self.assertEqual(bc.red_flags("Happy to hop on a call any time this week."), [])

    def test_check_is_not_checking(self):
        self.assertEqual(bc.red_flags("I am checking with my sources."), [])

    def test_urls(self):
        self.assertEqual(bc.extract_urls(PITCH), [CLIP, "https://janedoe.example/about"])

    def test_emails(self):
        self.assertEqual(bc.extract_emails(PITCH), ["jane.doe@gmail.com"])
        self.assertEqual(bc.extract_emails("logo@2x.png"), [])

    def test_outlets_without_clips(self):
        outlets = bc.claimed_outlets(PITCH)
        self.assertEqual([name for name, _ in outlets], ["WIRED", "Business Insider"])
        self.assertEqual(bc.unbacked_outlets(outlets, bc.extract_urls(PITCH)), ["Business Insider"])

    def test_registrable_domain(self):
        self.assertEqual(bc.registrable_domain("www.janedoe.co.uk"), "janedoe.co.uk")
        self.assertEqual(bc.registrable_domain("blog.janedoe.com"), "janedoe.com")
        self.assertEqual(bc.registrable_domain("WWW.Example.COM."), "example.com")
        self.assertEqual(bc.registrable_domain("janedoe.example"), "janedoe.example")


class PersonaTests(unittest.TestCase):
    def test_documented_persona(self):
        found = bc.persona_matches("Ervin Hoskins")
        self.assertEqual([p["name"] for p in found], ["Ervin B. Hoskins"])
        self.assertEqual(found[0]["kind"], "invented")
        self.assertEqual(found[0]["source"], bc.OPENAI_2026)
        self.assertIn("Middle East Monitor", found[0]["outlets"])

    def test_accents_and_titles(self):
        self.assertEqual([p["name"] for p in bc.persona_matches("Genevieve Tremblay")], ["Geneviève Tremblay"])
        self.assertEqual([p["name"] for p in bc.persona_matches("Dr. Alice Johnson")], ["Alice Johnson"])

    def test_hyphenated_name(self):
        self.assertEqual([p["name"] for p in bc.persona_matches("Ruth Jackson-Kirby")], ["Ruth Jackson-Kirby"])

    def test_kinds_filter(self):
        self.assertEqual(bc.persona_matches("Eleni Nicolaou", kinds=("invented",)), [])
        self.assertEqual([p["kind"] for p in bc.persona_matches("Eleni Nicolaou")], ["fake_expert"])

    def test_no_match(self):
        self.assertEqual(bc.persona_matches("Jane Doe"), [])
        self.assertEqual(bc.persona_matches("Williams"), [])
        self.assertEqual(bc.persona_matches("Jenny Williamson"), [])
        self.assertEqual(bc.persona_matches(""), [])

    def test_every_case_is_sourced(self):
        names = []
        for case in bc.PERSONAS:
            name = case["name"]
            names.append(name)
            self.assertIn(case["kind"], bc.CASE_KINDS, name)
            self.assertTrue(case["sources"], name)
            for source in case["sources"]:
                self.assertTrue(source.startswith("https://"), name)
            self.assertTrue(case["what"].endswith("."), name)
            self.assertRegex(case["reported"], r"^\d{4}-\d{2}$")
            for outlet in case["outlets"]:
                self.assertTrue(outlet["name"], name)
                domain = outlet["domain"]
                if domain is not None:
                    self.assertTrue(re.match(r"^[a-z0-9.\-]+\.[a-z]{2,}$", domain), domain)
                    self.assertFalse(domain.startswith("www."), domain)
        self.assertEqual(len(names), len(set(names)))

    def test_markdown(self):
        md = bc.render_markdown(bc.run_checks("Margaux Blanchard", "Hello"))
        self.assertIn("Margaux Blanchard was the byline of stories WIRED", md)
        self.assertIn("Documented outlets: WIRED, Business Insider, SFGate", md)
        self.assertIn("Real people share names", md)
        md = bc.render_markdown(bc.run_checks("Caroline Williams", "Hello"))
        self.assertIn("Caroline Williams is the name of a real science journalist.", md)
        self.assertIn("Unless this is a namesake", md)
        self.assertNotIn("Real people share names", md)
        md = bc.render_markdown(bc.run_checks("Ruth Jackson-Kirby", "Hello"))
        self.assertIn("Ruth Jackson-Kirby is the name of a real UK personal-finance journalist.", md)


class DatasetTests(unittest.TestCase):
    def test_dataset_is_json(self):
        data = json.loads(json.dumps(bc.cases_dataset()))
        self.assertEqual(data["cases"], bc.PERSONAS)
        self.assertEqual(data["version"], bc.__version__)

    @unittest.skipUnless(os.path.exists(DATASET), "personas.json not next to the tests")
    def test_personas_json_matches_code(self):
        with open(DATASET, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["kinds"], bc.CASE_KINDS)
        for want, have in zip(bc.PERSONAS, data["cases"]):
            self.assertEqual(have, want, want["name"])
        self.assertEqual(len(data["cases"]), len(bc.PERSONAS))


class PersonaClipTests(unittest.TestCase):
    def test_persona_byline_on_documented_outlet(self):
        page = bc.analyze_page(PERSONA_PAGE, "Jane Doe", "https://www.fairobserver.com/region/op-ed/")
        self.assertEqual(page["persona_bylines"], [{"name": "Alice Johnson", "byline": "Alice Johnson",
                                                    "source": bc.OPENAI_2026, "outlet": "Fair Observer"}])

    def test_persona_byline_elsewhere(self):
        page = bc.analyze_page(PERSONA_PAGE, "Jane Doe", "https://news.example/op-ed/")
        self.assertEqual(len(page["persona_bylines"]), 1)
        self.assertIsNone(page["persona_bylines"][0]["outlet"])

    def test_persona_author_page_url(self):
        page = bc.analyze_page(PERSONA_AUTHOR_URL, "Jane Doe", "https://www.middleeastmonitor.com/20260501-column/")
        self.assertEqual([(p["name"], p["outlet"]) for p in page["persona_bylines"]],
                         [("Ervin B. Hoskins", "Middle East Monitor")])

    def test_impersonated_writer_is_not_a_persona_byline(self):
        self.assertEqual(bc.persona_bylines(["Caroline Williams"], url="https://www.science.org/x"), [])

    def test_fake_expert_quoted_in_clip(self):
        page = bc.analyze_page(PERSONA_PAGE, "Jane Doe")
        self.assertEqual(page["people_quoted"], ["Eleni Nicolaou"])
        self.assertEqual([p["name"] for p in page["fake_experts_quoted"]], ["Eleni Nicolaou"])

    def test_clip_lines(self):
        url = "https://www.fairobserver.com/region/op-ed/"
        clip = bc.check_clip(url, "Jane Doe", fake_fetch({url: ok(url, PERSONA_PAGE)}))
        lines = "\n".join(bc._clip_lines(clip))
        self.assertIn("the byline Alice Johnson matches Alice Johnson, a documented invented persona. "
                      "This clip is on Fair Observer", lines)
        self.assertIn("the clip quotes Eleni Nicolaou, the name of an art-therapist persona", lines)
        json.dumps(clip)


class LookalikeTests(unittest.TestCase):
    def test_kuow_address(self):
        self.assertEqual(bc.lookalike_addresses(["k.campbelkuow.org@gmail.com"]),
                         [{"address": "k.campbelkuow.org@gmail.com", "looks_like": "campbelkuow.org"}])

    def test_outlet_domain_inside_name(self):
        self.assertEqual(bc.lookalike_addresses(["NYTimes.com.Desk@Outlook.com"]),
                         [{"address": "NYTimes.com.Desk@Outlook.com", "looks_like": "nytimes.com"}])

    def test_ordinary_addresses(self):
        self.assertEqual(bc.lookalike_addresses(["jane.doe@gmail.com", "minecraft.comics@gmail.com",
                                                 "desk@kuow.org", "nytimes.com@janedoe.example", "nobody"]), [])

    def test_markdown(self):
        report = bc.run_checks("Katie Campbell", "I'd love to feature your book. Reply to k.campbelkuow.org@gmail.com")
        self.assertEqual(report["pitch_addresses"], ["k.campbelkuow.org@gmail.com"])
        md = bc.render_markdown(report)
        self.assertIn("k.campbelkuow.org@gmail.com is a free webmail address", md)
        self.assertIn("Katie Campbell is the name of a real KUOW reporter.", md)
        json.dumps(report)


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.sender = bc.parse_email(EML)

    def test_detected(self):
        self.assertTrue(bc.looks_like_email(EML))
        self.assertTrue(bc.looks_like_email("Hi there", "pitch.EML"))
        self.assertFalse(bc.looks_like_email(PITCH, "pitch.txt"))

    def test_headers(self):
        self.assertEqual(self.sender["from"], ["jane@janedoe.example"])
        self.assertEqual(self.sender["reply_to"], ["jane.doe.writer@gmail.com"])
        self.assertEqual(self.sender["subject"], "Pitch: Minecraft weddings")

    def test_only_top_auth_header(self):
        self.assertEqual(self.sender["auth"], {"spf": "softfail", "dkim": "none", "dmarc": "fail"})

    def test_body(self):
        self.assertTrue(self.sender["text"].startswith("Pitch: Minecraft weddings"))
        self.assertIn("only communicate by email", self.sender["text"])

    def test_notes(self):
        notes = bc.sender_notes(self.sender)
        self.assertEqual(len(notes), 2)
        self.assertIn("replies go to jane.doe.writer@gmail.com", notes[0])
        self.assertIn("DMARC=fail, SPF=softfail", notes[1])

    def test_clean_sender_has_no_notes(self):
        self.assertEqual(bc.sender_notes({"from": ["a@b.example"], "reply_to": ["a@b.example"],
                                          "auth": {"spf": "pass", "dkim": "pass"}}), [])

    def test_html_body(self):
        sender = bc.parse_email(EML_HTML)
        self.assertEqual(sender["from"], ["sam@roe.example"])
        self.assertIn("pay me via PayPal", sender["text"])
        self.assertNotIn("hidden", sender["text"])

    def test_run_with_sender(self):
        report = bc.run_checks("Jane Doe", self.sender["text"], sender=self.sender)
        self.assertEqual(report["pitch_addresses"], ["jane@janedoe.example", "jane.doe.writer@gmail.com"])
        self.assertEqual(report["domains_to_check"], ["janedoe.example"])
        self.assertEqual(report["free_mail_domains"], ["gmail.com"])
        self.assertEqual([f["flag"] for f in report["pitch_flags"]], ["email-only"])
        self.assertEqual(report["persona_matches"], [])
        self.assertEqual(report["lookalike_addresses"], [])
        md = bc.render_markdown(report)
        self.assertIn("Sent from: jane@janedoe.example", md)
        self.assertIn("replies go to", md)
        json.dumps(report)


class SiteTests(unittest.TestCase):
    def test_site_pages(self):
        self.assertEqual(bc.site_pages("janedoe.example"), [
            "https://janedoe.example", "https://janedoe.example/contact", "https://janedoe.example/about"])
        self.assertEqual(bc.site_pages("https://janedoe.example/me"), ["https://janedoe.example/me"])

    def test_cfemail(self):
        self.assertEqual(bc.decode_cfemail(cf_encode("hidden@janedoe.example")), "hidden@janedoe.example")

    def test_page_emails(self):
        html = ('<a href="mailto:Jane@JaneDoe.example?subject=Hi">x</a>'
                '<a href="/cdn-cgi/l/email-protection#%s">[email protected]</a>'
                '<p>Or write to desk@janedoe.example. Logo: logo@2x.png</p>' % cf_encode("hidden@janedoe.example"))
        self.assertEqual(bc.page_emails(html),
                         ["jane@janedoe.example", "hidden@janedoe.example", "desk@janedoe.example"])

    def test_compare(self):
        self.assertIsNone(bc.compare_contacts(["a@x.example"], None))
        self.assertIsNone(bc.compare_contacts([], ["a@x.example"]))
        self.assertEqual(bc.compare_contacts(["a@x.example"], []), "none_listed")
        self.assertEqual(bc.compare_contacts(["a@x.example"], ["a@x.example", "b@x.example"]), "match")
        self.assertEqual(bc.compare_contacts(["a@gmail.com"], ["a@x.example"]), "mismatch")

    def test_site_unreachable(self):
        res = bc.check_site_contacts("janedoe.example", fake_fetch({}))
        self.assertEqual(res["error"], "HTTP 404")
        self.assertEqual(res["pages_read"], [])


class DraftTests(unittest.TestCase):
    def test_quotes(self):
        self.assertEqual(bc.extract_quotes(DRAFT),
                         ["We wanted our friends from every continent to be there with us,"])

    def test_search_links(self):
        links = bc.search_links("We wanted our friends from every continent to be there with us,")
        self.assertTrue(links["google"].startswith("https://www.google.com/search?q=%22We+wanted+our"))
        self.assertTrue(links["google"].endswith("with+us%22"))

    def test_draft_people(self):
        self.assertEqual(bc.quoted_people(DRAFT, exclude="Jane Doe"), ["Maria Lopez"])

    def test_writer_excluded(self):
        self.assertEqual(bc.quoted_people("It works, said Jane Doe.", exclude="Jane Doe"), [])

    def test_fake_expert_in_draft(self):
        report = bc.run_checks("Jane Doe", "Hello", EXPERT_DRAFT)
        self.assertEqual(report["draft_people_quoted"], ["Eleni Nicolaou", "Maria Lopez"])
        self.assertEqual([p["name"] for p in report["draft_fake_experts"]], ["Eleni Nicolaou"])
        self.assertEqual(report["draft_fake_experts"][0]["quoted_as"], "Eleni Nicolaou")
        md = bc.render_markdown(report)
        self.assertIn("the draft quotes Eleni Nicolaou, the name of an art-therapist persona", md)
        self.assertIn(bc.PG_EXPERTS, md)
        json.dumps(report)

    def test_no_fake_expert(self):
        self.assertEqual(bc.run_checks("Jane Doe", "Hello", DRAFT)["draft_fake_experts"], [])


class ParseTests(unittest.TestCase):
    def test_cdx(self):
        self.assertEqual(bc.parse_cdx(CDX_REPLY), "2019-04-05")
        self.assertIsNone(bc.parse_cdx("[]"))
        self.assertIsNone(bc.parse_cdx(""))

    def test_cdx_row(self):
        self.assertEqual(bc.parse_cdx_row(LATEST_REPLY), ("20260901000000", CLIP))
        self.assertIsNone(bc.parse_cdx_row('[["timestamp","original"],["x","y"]]'))

    def test_wayback_urls(self):
        self.assertIn("limit=-1", bc.wayback_latest_api(CLIP))
        self.assertIn("statuscode%3A200", bc.wayback_latest_api(CLIP))
        self.assertEqual(bc.archived_copy_url("20260901000000", CLIP),
                         "https://web.archive.org/web/20260901000000id_/" + CLIP)

    def test_rdap(self):
        self.assertEqual(bc.parse_rdap(RDAP_REPLY), "2026-08-01")
        self.assertIsNone(bc.parse_rdap('{"events": []}'))

    def test_fetch_refuses_non_http(self):
        self.assertEqual(bc.fetch("file:///etc/passwd")["error"], "not an http(s) URL")


class ClipTests(unittest.TestCase):
    def test_blocked_clip_read_from_wayback(self):
        live = {"status": 403, "url": CLIP, "text": None, "error": "HTTP 403"}
        clip = bc.check_clip(CLIP, "Jane Doe", fake_fetch(archived(live, ARTICLE)))
        self.assertEqual(clip["read_from"], "wayback")
        self.assertEqual(clip["archived_on"], "2026-09-01")
        self.assertTrue(clip["byline_match"])
        lines = "\n".join(bc._clip_lines(clip))
        self.assertIn("Could not load:** HTTP 403", lines)
        self.assertIn("Wayback Machine's copy of 2026-09-01", lines)
        self.assertIn("Byline in page data: yes", lines)

    def test_bot_check_page_read_from_wayback(self):
        clip = bc.check_clip(CLIP, "Jane Doe", fake_fetch(archived(ok(CLIP, CHALLENGE), ARTICLE)))
        self.assertTrue(clip["blocked"])
        self.assertEqual(clip["read_from"], "wayback")
        self.assertTrue(clip["byline_match"])
        self.assertIn("bot check page", "\n".join(bc._clip_lines(clip)))

    def test_removed_clip_shows_old_byline(self):
        live = {"status": 404, "url": CLIP, "text": None, "error": "HTTP 404"}
        clip = bc.check_clip(CLIP, "Jane Doe", fake_fetch(archived(live, ARTICLE)))
        lines = "\n".join(bc._clip_lines(clip))
        self.assertIn("HTTP 404, page not found", lines)
        self.assertIn("Byline in page data: yes (Jane Q. Doe; Sam Roe)", lines)

    def test_redirect_to_home(self):
        url = "https://www.example.com/story/1"
        pages = {url: ok("https://www.example.com/", "<html><head><title>Home</title></head></html>")}
        clip = bc.check_clip(url, "Jane Doe", fake_fetch(pages))
        self.assertTrue(clip["redirected_home"])
        self.assertIsNone(clip["read_from"])
        self.assertEqual(clip["title"], "")
        self.assertEqual(clip["persona_bylines"], [])
        self.assertIn("home page", "\n".join(bc._clip_lines(clip)))

    def test_author_links_listed_when_no_match(self):
        clip = bc.check_clip(CLIP, "John Smith", fake_fetch({CLIP: ok(CLIP, YOAST)}))
        lines = "\n".join(bc._clip_lines(clip))
        self.assertIn("byline in page data is Jane Doe", lines)
        self.assertIn("Author links in page data: https://www.facebook.com/examplemag", lines)


class RunTests(unittest.TestCase):
    def setUp(self):
        pages = {
            CLIP: ok(CLIP, ARTICLE),
            bc.wayback_api(CLIP): ok(bc.wayback_api(CLIP), CDX_REPLY),
            bc.RDAP_URL + "janedoe.example": ok(bc.RDAP_URL + "janedoe.example", RDAP_REPLY),
            bc.wayback_api("janedoe.example"): ok(bc.wayback_api("janedoe.example"), "[]"),
            "https://janedoe.example": ok("https://janedoe.example", SITE_HTML),
        }
        self.report = bc.run_checks("Jane Doe", PITCH, DRAFT, clips=[], sites=["https://janedoe.example"],
                                    fetch_fn=fake_fetch(pages), today=date(2026, 10, 13))

    def test_clip(self):
        clip = self.report["clips"][0]
        self.assertEqual(clip["status"], 200)
        self.assertEqual(clip["read_from"], "live")
        self.assertTrue(clip["byline_match"])
        self.assertEqual(clip["first_archived"], "2019-04-05")

    def test_missing_clip(self):
        clip = self.report["clips"][1]
        self.assertEqual(clip["status"], 404)
        self.assertEqual(clip["error"], "HTTP 404")
        self.assertIsNone(clip["read_from"])

    def test_domain(self):
        dom = self.report["domains"][0]
        self.assertEqual(dom["domain"], "janedoe.example")
        self.assertEqual(dom["registered"], "2026-08-01")
        self.assertEqual(dom["age_days"], 73)
        self.assertTrue(dom["new"])
        self.assertIsNone(dom["first_archived"])

    def test_free_mail_not_checked(self):
        self.assertEqual(self.report["free_mail_domains"], ["gmail.com"])
        self.assertEqual(self.report["domains_to_check"], ["janedoe.example"])

    def test_site_contact_mismatch(self):
        site = self.report["site_contacts"][0]
        self.assertEqual(site["emails"], ["jane@janedoe.example"])
        self.assertEqual(site["pages_read"], ["https://janedoe.example"])
        self.assertIsNone(site["error"])
        self.assertEqual(self.report["contact_match"], "mismatch")

    def test_markdown(self):
        md = bc.render_markdown(self.report)
        self.assertIn("# Pitch verification worksheet: Jane Doe", md)
        self.assertIn("Business Insider", md)
        self.assertIn("less than a year old", md)
        self.assertIn("HTTP 404, page not found", md)
        self.assertIn("https://janedoe.example lists: jane@janedoe.example", md)
        self.assertIn("the pitch came from jane.doe@gmail.com, but the writer's own site lists", md)
        self.assertIn("Still to do by a person", md)
        self.assertIn("Alex Moreno", md)
        self.assertIn("ask how they verified the writer", md)
        self.assertIn("exists outside expert-matching services", md)

    def test_json_serialisable(self):
        json.dumps(self.report)


class CliTests(unittest.TestCase):
    def test_offline_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            pitch = os.path.join(tmp, "pitch.txt")
            out = os.path.join(tmp, "sheet.md")
            with open(pitch, "w", encoding="utf-8") as fh:
                fh.write(PITCH)
            self.assertEqual(bc.main(["--name", "Jane Doe", "--pitch", pitch, "--offline", "--out", out]), 0)
            with open(out, encoding="utf-8") as fh:
                sheet = fh.read()
        self.assertIn("Not fetched (offline): " + CLIP, sheet)
        self.assertIn("Email-only contact", sheet)
        self.assertNotIn("Sent from:", sheet)

    def test_offline_eml(self):
        with tempfile.TemporaryDirectory() as tmp:
            pitch = os.path.join(tmp, "pitch.eml")
            out = os.path.join(tmp, "sheet.md")
            with open(pitch, "w", encoding="utf-8") as fh:
                fh.write(EML)
            self.assertEqual(bc.main(["--name", "Jane Doe", "--pitch", pitch, "--offline", "--out", out]), 0)
            with open(out, encoding="utf-8") as fh:
                sheet = fh.read()
        self.assertIn("Sent from: jane@janedoe.example", sheet)
        self.assertIn("replies go to jane.doe.writer@gmail.com", sheet)
        self.assertIn("Email-only contact", sheet)
        self.assertIn("Not checked (offline): janedoe.example", sheet)

    def test_offline_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "r.json")
            bc.main(["--name", "Jane Doe", "--clip", CLIP, "--offline", "--json", "--out", out])
            with open(out, encoding="utf-8") as fh:
                data = json.load(fh)
        self.assertTrue(data["offline"])
        self.assertEqual(data["clip_urls"], [CLIP])
        self.assertEqual(data["clips"], [])
        self.assertIsNone(data["sender"])
        self.assertEqual(data["persona_matches"], [])
        self.assertEqual(data["draft_fake_experts"], [])

    def test_offline_persona_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "sheet.md")
            self.assertEqual(bc.main(["--name", "Noah Lamington", "--offline", "--out", out]), 0)
            with open(out, encoding="utf-8") as fh:
                sheet = fh.read()
        self.assertIn("Noah Lamington was the byline of one of seven fake journalist personas", sheet)
        self.assertIn("Documented outlets: Asia Times, International Policy Digest.", sheet)
        self.assertIn(bc.OPENAI_2026, sheet)

    def test_cases_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "personas.json")
            self.assertEqual(bc.main(["--cases", "--out", out]), 0)
            with open(out, encoding="utf-8") as fh:
                data = json.load(fh)
        self.assertEqual(data["cases"], bc.PERSONAS)
        self.assertEqual(data["dataset"], "byline-check documented cases")

    def test_name_required_without_cases(self):
        with self.assertRaises(SystemExit):
            bc.main(["--offline"])


if __name__ == "__main__":
    unittest.main()
