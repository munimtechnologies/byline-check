import json
import os
import sys
import tempfile
import unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import byline_check as bc  # noqa: E402

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

REMOVED = """<html><head><meta name="byl" content="By Margo Example"></head><body>
<p>Editor&rsquo;s note: This article has been removed after we determined the author was
impersonating an established journalist.</p></body></html>"""

PITCH = """Hi, I'm Jane Doe, a freelancer who has written for WIRED and Business Insider.
Clips: https://www.wired.com/story/minecraft-weddings/ and https://janedoe.example/about.
I'm travelling, so I can only communicate by email for now. Could you pay me via PayPal?
jane.doe@gmail.com"""

DRAFT = """Couples now marry inside games. "We wanted our friends from every continent to be there with us," said Maria Lopez, who married in March.
"Short one," she said."""

CLIP = "https://www.wired.com/story/minecraft-weddings/"
CDX_REPLY = '[["timestamp","original"],["20190405123456","https://www.wired.com/story/minecraft-weddings/"]]'
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


class PageTests(unittest.TestCase):
    def setUp(self):
        self.page = bc.analyze_page(ARTICLE, "Jane Doe")

    def test_title(self):
        self.assertEqual(self.page["title"], "Minecraft weddings")

    def test_bylines_from_meta_jsonld_and_rel_author(self):
        self.assertEqual(set(self.page["bylines"]), {"Jane Q. Doe", "Sam Roe"})
        self.assertTrue(self.page["byline_match"])

    def test_people_quoted(self):
        self.assertEqual(self.page["people_quoted"], ["Alex Moreno", "Priya Shah", "Lee Park"])

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

    def test_outlets_without_clips(self):
        outlets = bc.claimed_outlets(PITCH)
        self.assertEqual([name for name, _ in outlets], ["WIRED", "Business Insider"])
        self.assertEqual(bc.unbacked_outlets(outlets, bc.extract_urls(PITCH)), ["Business Insider"])

    def test_registrable_domain(self):
        self.assertEqual(bc.registrable_domain("www.janedoe.co.uk"), "janedoe.co.uk")
        self.assertEqual(bc.registrable_domain("blog.janedoe.com"), "janedoe.com")
        self.assertEqual(bc.registrable_domain("WWW.Example.COM."), "example.com")
        self.assertEqual(bc.registrable_domain("janedoe.example"), "janedoe.example")


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


class ParseTests(unittest.TestCase):
    def test_cdx(self):
        self.assertEqual(bc.parse_cdx(CDX_REPLY), "2019-04-05")
        self.assertIsNone(bc.parse_cdx("[]"))
        self.assertIsNone(bc.parse_cdx(""))

    def test_rdap(self):
        self.assertEqual(bc.parse_rdap(RDAP_REPLY), "2026-08-01")
        self.assertIsNone(bc.parse_rdap('{"events": []}'))

    def test_fetch_refuses_non_http(self):
        self.assertEqual(bc.fetch("file:///etc/passwd")["error"], "not an http(s) URL")


class RunTests(unittest.TestCase):
    def setUp(self):
        pages = {
            CLIP: ok(CLIP, ARTICLE),
            bc.wayback_api(CLIP): ok(bc.wayback_api(CLIP), CDX_REPLY),
            bc.RDAP_URL + "janedoe.example": ok(bc.RDAP_URL + "janedoe.example", RDAP_REPLY),
            bc.wayback_api("janedoe.example"): ok(bc.wayback_api("janedoe.example"), "[]"),
        }
        self.report = bc.run_checks("Jane Doe", PITCH, DRAFT, clips=[], sites=["https://janedoe.example"],
                                    fetch_fn=fake_fetch(pages), today=date(2026, 10, 13))

    def test_clip(self):
        clip = self.report["clips"][0]
        self.assertEqual(clip["status"], 200)
        self.assertTrue(clip["byline_match"])
        self.assertEqual(clip["first_archived"], "2019-04-05")

    def test_missing_clip(self):
        clip = self.report["clips"][1]
        self.assertEqual(clip["status"], 404)
        self.assertEqual(clip["error"], "HTTP 404")

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

    def test_markdown(self):
        md = bc.render_markdown(self.report)
        self.assertIn("# Pitch verification worksheet: Jane Doe", md)
        self.assertIn("Business Insider", md)
        self.assertIn("less than a year old", md)
        self.assertIn("Could not load:** HTTP 404", md)
        self.assertIn("Still to do by a person", md)
        self.assertIn("Alex Moreno", md)

    def test_json_serialisable(self):
        json.dumps(self.report)

    def test_live_clip_marked(self):
        self.assertEqual(self.report["clips"][0]["read_from"], "live")
        self.assertIsNone(self.report["clips"][1]["read_from"])

    def test_blocked_clip_read_from_wayback(self):
        day = date(2026, 10, 13)
        pages = {
            CLIP: {"status": 403, "url": CLIP, "text": None, "error": "HTTP 403"},
            bc.wayback_api(CLIP): ok(bc.wayback_api(CLIP), CDX_REPLY),
            bc.archived_copy_url(CLIP, day): ok(bc.archived_copy_url(CLIP, day), ARTICLE),
        }
        clip = bc.check_clip(CLIP, "Jane Doe", fake_fetch(pages), day)
        self.assertEqual(bc.archived_copy_url(CLIP, day),
                         "https://web.archive.org/web/20261013id_/" + CLIP)
        self.assertEqual(clip["read_from"], "wayback")
        self.assertTrue(clip["byline_match"])
        lines = "\n".join(bc._clip_lines(clip))
        self.assertIn("Could not load:** HTTP 403", lines)
        self.assertIn("Wayback Machine's latest saved copy", lines)
        self.assertIn("Byline in page data: yes", lines)

    def test_redirect_to_home(self):
        url = "https://www.example.com/story/1"
        pages = {url: ok("https://www.example.com/", "<html><body>Home</body></html>")}
        clip = bc.check_clip(url, "Jane Doe", fake_fetch(pages))
        self.assertTrue(clip["redirected_home"])
        self.assertIn("home page", "\n".join(bc._clip_lines(clip)))


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

    def test_offline_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "r.json")
            bc.main(["--name", "Jane Doe", "--clip", CLIP, "--offline", "--json", "--out", out])
            with open(out, encoding="utf-8") as fh:
                data = json.load(fh)
        self.assertTrue(data["offline"])
        self.assertEqual(data["clip_urls"], [CLIP])
        self.assertEqual(data["clips"], [])


if __name__ == "__main__":
    unittest.main()
