# byline-check

A verification worksheet for editors vetting a freelance pitch.

Between 2025 and 2026, invented or impersonated freelancers got stories into WIRED, Business
Insider, Science, the Ottawa Citizen, the Guardian and many other outlets. In October 2026 OpenAI
reported an operation that placed almost 100 articles in about a dozen outlets under seven
fake journalist bylines. The editors who caught these writers did it with simple checks. They
tried to pay the writer through the normal payments system. They contacted people quoted in the
writer's earlier clips. They asked for a live call, and they searched for quotes that had already
been published elsewhere. AI-text detectors did not catch them: two detectors rated the
fabricated WIRED feature as likely human-written.

`byline-check` runs the mechanical part of those checks in one go and prints a worksheet. It
**does not** decide whether a writer is real, and it does no AI-text detection. It shows you
evidence and lists what a person still has to verify.

```
python byline_check.py --name "Jane Doe" --pitch pitch.eml --draft draft.txt --site janedoe.com
```

Python 3.8+, standard library only, one file. MIT licensed.

## What it checks

| Input | Check |
|---|---|
| Writer's name (`--name`) | Whether the name is a byline already documented as an invented persona (the seven 'Bogus Bylines' personas, 'Margaux Blanchard', 'Daniel Robson', We News staff personas), or a real writer documented as impersonated. Each match gives its public source. Real people share names, so a match is a reason to verify, not proof. The full list and its sources are in [CASES.md](CASES.md). |
| Pitch and emails (`--pitch`, a text file or a saved `.eml` email) | Phrases that match documented fake-freelancer patterns, such as email-only contact ("can't do a call") or payment outside the normal system (PayPal, checks, gift cards, crypto). Each flag says which case it comes from. |
| | Outlets the pitch names (WIRED, Business Insider, The Guardian and about 60 more) that none of the supplied clips comes from. |
| | Every link in the pitch is treated as a claimed clip. |
| | Webmail addresses dressed up as an organisation's, such as `k.campbelkuow.org@gmail.com`, the kind of address used to impersonate a KUOW reporter in 2026. |
| | From a saved email: the sending address, a Reply-To that points somewhere else, and SPF, DKIM or DMARC failures recorded by your own mail server. |
| Claimed clips (`--clip URL`, repeatable) | Does the page load? Is it gone (404) or redirected to the home page, which can mean the story was removed? Whose byline is in the page data (meta tags, schema.org JSON-LD including Yoast-style `@id` references, `rel=author`, author-page URLs)? Does the page carry an editor's note, a removal notice or the word "impersonating"? When did the Wayback Machine first save it? Who is quoted in it, so you can contact them yourself? If the live page refuses scripts, sends a bot check page or is gone, the byline is read from the Wayback Machine's latest normal capture instead. |
| Writer's own site (`--site`) | The email addresses the site lists (including `mailto:` links and Cloudflare-hidden addresses) on the given page, or on the home, `/contact` and `/about` pages. If none of them is the address the pitch came from, the worksheet says so. That is the impersonation pattern from the 2026 Science case. |
| Writer's domains (`--site`, plus any non-webmail address in the pitch) | Registration date from RDAP (flagged if less than a year old) and first Wayback Machine capture. |
| Submitted draft (`--draft`) | Every direct quote of 8 words or more, each with exact-phrase search links for Google, Bing and DuckDuckGo, so you can see whether it was lifted from an earlier story. The worksheet also lists the people named as sources. |

Then it lists the steps no tool can do for you: a live call that tests the writer on their own
pitch, confirming the pitch through contact details you find yourself, payment through your
normal system, contacting earlier sources and editors (and asking how those editors verified the
writer), asking for an annotated draft or version history, and confirming every quote before
publication.

## Usage

```
python byline_check.py --name NAME [--pitch FILE] [--draft FILE] [--clip URL ...]
                       [--site DOMAIN ...] [--offline] [--json] [--out FILE]
```

- `--pitch` takes plain text or a saved email. In Gmail use "Download message" and in Outlook
  "Save as"; any file ending in `.eml`, or a file that starts with raw email headers, is read as
  an email.
- `--offline` checks the text only and fetches nothing.
- `--json` prints the full machine-readable report instead of Markdown.
- `--out sheet.md` writes the worksheet to a UTF-8 file.

### If someone says they are a reporter

The same checks work the other way round. In 2026 scammers posing as a KUOW reporter emailed at
least 43 book authors from lookalike Gmail addresses and then asked them to pay for interviews.
If a "reporter" writes to you, save the email and run it against the newsroom's own site:

```
python byline_check.py --name "Reporter Name" --pitch invitation.eml --site newsroom.example
```

The worksheet shows a webmail address dressed up as the newsroom's, and whether the newsroom's
pages list the address the email came from. Then confirm with the newsroom itself, through contact
details you find yourself, that the person works there. KUOW says it does not offer or accept
money for interviews or coverage, so a request to pay is a warning sign.

Example (fictional names and domains), abridged:

```
# Pitch verification worksheet: Jane Doe

## 1. Pitch and correspondence
- Sent from: jane@janedoe.example
- **Check:** replies go to jane.doe.writer@gmail.com, not the sending address (jane@janedoe.example). ...
- **Email-only contact:** "...I'm travelling, so I can only communicate by email for now..." The fake
  'Daniel Robson' told the Ottawa Citizen he could only communicate by email; ...
- **Check:** outlets named in the pitch with no clip supplied from them: Business Insider

## 2. Claimed clips
### https://www.example-magazine.com/story/minecraft-weddings/
- **Check:** HTTP 404, page not found: the story may have been removed, or the link is wrong
- Read from the Wayback Machine's copy of 2026-09-01 instead, so a later removal would not show here
- Byline in page data: yes (Jane Q. Doe)
- First saved by the Wayback Machine: 2019-04-05
- People or organisations quoted (contact them yourself): Alex Moreno, Priya Shah

## 3. Writer's own site and domains
- janedoe.example: registered 2026-08-01 (73 days ago) **less than a year old**; ...
- https://janedoe.example lists: desk@janedoe.example
- **Check:** the pitch came from jane@janedoe.example, jane.doe.writer@gmail.com, but the writer's own
  site lists desk@janedoe.example. ...
```

## What it sends over the network

Without `--offline`, the tool fetches each clip URL directly, and the pages of each `--site`
described above. It sends each clip URL and domain to the Wayback Machine's CDX API
(web.archive.org), and fetches saved copies from it when a live clip can't be read. It sends each
domain to rdap.org. It sends nothing else anywhere. It never sends the pitch, the email or the
draft. The search links are only printed, not opened. The list of documented personas is built
in, so checking a name sends nothing. Some news sites refuse requests from scripts (HTTP 403) or
answer with a bot check page; the worksheet then falls back to the Wayback Machine and tells you
to open the link in a browser.

## Limits

- A matching byline shows that the clip exists, not that the person pitching you wrote it. The
  impostor in the Science case used a real writer's name and clips. Confirm the pitch through
  the writer's own contact details.
- The persona list only holds names documented in published reporting, and several of them
  (Jenny Williams, Alice Johnson, Michael Harrison, Sophia Gonzalez) are common names. A match
  says "verify", never "fake". A name that is not on the list tells you nothing.
- Bylines are matched by words, so "Jane Doe" matches "Jane Q. Doe". A missing byline in the page
  data is a reason to look, not proof. Some sites only put bylines in rendered JavaScript.
- The list of quoted people comes from attribution patterns ("said X", "X, a ..., said",
  "according to X"). It misses some names and sometimes lists organisations.
- A red-flag phrase is not evidence of fraud. Many real freelancers use PayPal or prefer email.
- Domain age says nothing about writers who use webmail. Most real freelancers use webmail too.
- Email checks read only the top `Authentication-Results` header, the one your own mail server
  added. A pass does not prove who wrote the message, only that the sending service was allowed
  to use that address.

## The cases behind the checks

Every check comes from a documented case. [CASES.md](CASES.md) maps each check to its cases and
sources. The main ones:

- WIRED, "How WIRED Got Rolled by an AI Freelancer" (Aug 2025): the writer could not complete
  WIRED's payments system and insisted on PayPal or a check, and two AI detectors passed the copy.
  Coverage: https://pressgazette.co.uk/publishers/digital-journalism/margaux-blanchard-wired-ai-editors-journalist/
  and https://talkingbiznews.com/media-news/how-wired-got-duped-by-an-ai-freelancer/
- The Local (Toronto), "Investigating a Possible Scammer in Journalism's AI Era" (Nov 2025): the
  editor contacted people quoted in a freelancer's earlier stories, and they said they had never
  spoken to her. https://thelocal.to/investigating-scam-journalism-ai/ The Local now asks authors
  for annotated drafts (Reuters Institute, below).
- Science, editor's note (16 Sept 2026): a story was removed because its author had impersonated
  an established science journalist, using her name and clips, and two of its quotes were found
  in other writers' earlier stories. Science's editors and the story's sources had only ever
  emailed the impostor. The same report describes Undark finding on a voice call that a writer
  did not know the material in her own pitch.
  https://www.cjr.org/analysis/fake-caroline-williams-science-nature-magazine-ai-influx-pitches.php
- Ottawa Citizen (29 Sept 2026): after removing columns by a persona that "does not seem to be a
  real person" and said he could only communicate by email, the paper now asks new opinion writers
  to meet a staff journalist in person and pose for a photo.
  https://www.cbc.ca/news/canada/daniel-robson-suspected-fake-ai-persona-9.7363967
- OpenAI, "Disrupting AI-enabled 'false front' operations" (8 Oct 2026): seven fake journalist
  bylines placed almost 100 articles in about a dozen outlets from July 2025 to October 2026;
  the operators used ChatGPT to fit drafts to each outlet's submission rules and to write pitch
  emails. https://openai.com/index/disrupting-ai-enabled-false-front-operations/ Marc Owen Jones
  traced the articles across 17 sites and found that one newspaper ran a column because it trusted
  the syndicator, without checking the author:
  https://marcowenjones.substack.com/p/operation-bogus-bylines-the-pro-iran
- The Canadian Press, "Byline or bot? AI-generated 'journalists' start to appear in Canada"
  (3 Oct 2026): the We News site's staff personas, and how the Daniel Robson persona came apart
  when he refused a video call.
  https://www.cp24.com/news/canada/2026/10/03/byline-or-bot-ai-generated-journalists-start-to-appear-in-canada/
- KUOW, "Scammers used AI to impersonate me, a KUOW reporter" (12 Oct 2026): lookalike Gmail
  addresses, at least 43 authors emailed, and requests for payment.
  https://kuow.org/technology/2026-10-12/scammers-used-ai-to-impersonate-me-a-kuow-reporter-heres-how-to-avoid-such-traps
- Press Gazette keeps a running tracker of these cases:
  https://pressgazette.co.uk/publishers/digital-journalism/ai-journalism-mistakes/
- Reuters Institute, "Speed, hoaxes and mistrust: How AI is transforming freelance journalism":
  https://reutersinstitute.politics.ox.ac.uk/news/speed-hoaxes-and-mistrust-how-ai-transforming-freelance-journalism

## Tests

```
python -m unittest -v test_byline_check.py
```

The tests use saved HTML, emails and API replies, so they need no network.

## Changes

- 0.3.0: flags a writer's name that matches a byline documented as an invented persona (OpenAI's
  seven 'Bogus Bylines' personas, 'Margaux Blanchard', 'Daniel Robson', We News personas) or a
  real writer documented as impersonated, with the source for each; flags webmail addresses
  dressed up as an organisation's (the 2026 KUOW case); the step on confirming earlier bylines
  now asks how those editors verified the writer; adds CASES.md and a section for people
  contacted by someone claiming to be a reporter.
- 0.2.0: reads saved `.eml` pitches (sender, Reply-To, SPF/DKIM/DMARC); compares the pitch
  address with the addresses on the writer's own site; follows Yoast-style JSON-LD `@id`
  author references and tolerates JSON-LD with raw newlines or comment wrappers; matches
  author-page URLs and no longer reports a Facebook page URL as a conflicting byline; detects
  bot check pages, 404s and home-page redirects and then reads the latest normal Wayback
  capture rather than whatever capture is nearest to today; two new human steps (confirm the pitch
  through the writer's own contact details; ask for an annotated draft).
- 0.1.0: first release.

## About

Made by MV2 of Munim, Inc. The code and this README were written with AI agents working in his
name. Issues and pull requests are welcome, especially new red-flag patterns and documented
personas that come from published cases (please include the source) and byline markup the parser
misses. Contact: munimversion2@gmail.com.
