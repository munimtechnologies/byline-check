# byline-check

A verification worksheet for editors vetting a freelance pitch.

Between 2025 and 2026, invented or impersonated freelancers got stories into WIRED, Business
Insider, Science, the Ottawa Citizen, the Guardian and many other outlets. The editors who caught
them did it with simple checks. They tried to pay the writer through the normal payments system.
They contacted people quoted in the writer's earlier clips. They asked for a live call, and they
searched for quotes that had already been published elsewhere. AI-text detectors did not catch
them: two detectors rated the fabricated WIRED feature as likely human-written.

`byline-check` runs the mechanical part of those checks in one go and prints a worksheet. It
**does not** decide whether a writer is real, and it does no AI-text detection. It shows you
evidence and lists what a person still has to verify.

```
python byline_check.py --name "Jane Doe" --pitch pitch.txt --draft draft.txt --site janedoe.com
```

Python 3.8+, standard library only, one file. MIT licensed.

## What it checks

| Input | Check |
|---|---|
| Pitch and emails (`--pitch`) | Phrases that match documented fake-freelancer patterns, such as email-only contact ("can't do a call") or payment outside the normal system (PayPal, checks, gift cards, crypto). Each flag says which case it comes from. |
| | Outlets the pitch names (WIRED, Business Insider, The Guardian and about 60 more) that none of the supplied clips comes from. |
| | Every link in the pitch is treated as a claimed clip. |
| Claimed clips (`--clip URL`, repeatable) | Does the page load? Does it redirect to the home page, which can mean the story was removed? Whose byline is in the page data (meta tags, schema.org JSON-LD, `rel=author`)? Does the page carry an editor's note, a removal notice or the word "impersonating"? When did the Wayback Machine first save it? Who is quoted in it, so you can contact them yourself? If the live page refuses scripts, the byline is read from the Wayback Machine's latest saved copy. |
| Writer's domains (`--site`, plus any non-webmail address in the pitch) | Registration date from RDAP (flagged if less than a year old) and first Wayback Machine capture. |
| Submitted draft (`--draft`) | Every direct quote of 8 words or more, each with exact-phrase search links for Google, Bing and DuckDuckGo, so you can see whether it was lifted from an earlier story. The worksheet also lists the people named as sources. |

Then it lists the steps no tool can do for you: a live call or meeting, payment through your
normal system, contacting earlier sources and earlier editors through channels you find yourself,
and confirming every quote before publication.

## Usage

```
python byline_check.py --name NAME [--pitch FILE] [--draft FILE] [--clip URL ...]
                       [--site DOMAIN ...] [--offline] [--json] [--out FILE]
```

- `--offline` checks the text only and fetches nothing.
- `--json` prints the full machine-readable report instead of Markdown.
- `--out sheet.md` writes the worksheet to a UTF-8 file.

Example (fictional names and domains), abridged:

```
# Pitch verification worksheet: Jane Doe

## 1. Pitch and correspondence
- **Email-only contact:** "...I'm travelling, so I can only communicate by email for now..." The fake
  'Daniel Robson' told the Ottawa Citizen he could only communicate by email; ...
- **Payment outside the normal system:** "...Could you pay me via PayPal?..." ...
- **Check:** outlets named in the pitch with no clip supplied from them: Business Insider

## 2. Claimed clips
### https://www.example-magazine.com/story/minecraft-weddings/
- Loaded: HTTP 200
- Byline in page data: yes (Jane Q. Doe)
- First saved by the Wayback Machine: 2019-04-05
- People or organisations quoted (contact them yourself): Alex Moreno, Priya Shah

## 3. Writer's own domains
- janedoe.example: registered 2026-08-01 (73 days ago) **less than a year old**; ...
```

## What it sends over the network

Without `--offline`, the tool fetches each clip URL directly. It sends each clip URL and domain
to the Wayback Machine's CDX API (web.archive.org) and each domain to rdap.org. It sends nothing
else anywhere. It never sends the pitch or the draft. The search links are only printed, not
opened. Some news sites refuse requests from scripts (HTTP 403); when that happens the worksheet
tells you to open the link in a browser.

## Limits

- Bylines are matched by words, so "Jane Doe" matches "Jane Q. Doe". A missing byline in the page
  data is a reason to look, not proof. Some sites only put bylines in rendered JavaScript.
- The list of quoted people comes from attribution patterns ("said X", "X, a ..., said",
  "according to X"). It misses some names and sometimes lists organisations.
- A red-flag phrase is not evidence of fraud. Many real freelancers use PayPal or prefer email.
- Domain age says nothing about writers who use webmail. Most real freelancers use webmail too.

## The cases behind the checks

- WIRED, "How WIRED Got Rolled by an AI Freelancer" (Aug 2025): the writer could not complete
  WIRED's payments system and insisted on PayPal or a check, and two AI detectors passed the copy.
  Coverage: https://pressgazette.co.uk/publishers/digital-journalism/margaux-blanchard-wired-ai-editors-journalist/
  and https://talkingbiznews.com/media-news/how-wired-got-duped-by-an-ai-freelancer/
- The Local (Toronto), "Investigating a Possible Scammer in Journalism's AI Era" (Nov 2025): the
  editor contacted people quoted in a freelancer's earlier stories, and they said they had never
  spoken to her. https://thelocal.to/investigating-scam-journalism-ai/
- Science, editor's note (16 Sept 2026): a story was removed because its author had impersonated
  an established science journalist, and two of its quotes were found in other writers' earlier
  stories. https://www.cjr.org/analysis/fake-caroline-williams-science-nature-magazine-ai-influx-pitches.php
- Ottawa Citizen (29 Sept 2026): after removing columns by a persona that "does not seem to be a
  real person" and said he could only communicate by email, the paper now asks new opinion writers
  to meet a staff journalist in person and pose for a photo.
  https://www.cbc.ca/news/canada/daniel-robson-suspected-fake-ai-persona-9.7363967
- Press Gazette keeps a running tracker of these cases:
  https://pressgazette.co.uk/publishers/digital-journalism/ai-journalism-mistakes/
- Reuters Institute, "Speed, hoaxes and mistrust: How AI is transforming freelance journalism":
  https://reutersinstitute.politics.ox.ac.uk/news/speed-hoaxes-and-mistrust-how-ai-transforming-freelance-journalism

## Tests

```
python -m unittest -v test_byline_check.py
```

The tests use saved HTML and API replies, so they need no network.

## About

Made by MV2 of Munim, Inc. The code and this README were written with AI agents working in his
name. Issues and pull requests are welcome, especially new red-flag patterns that come from
documented cases (please include the source) and byline markup the parser misses. Contact:
munimversion2@gmail.com.
