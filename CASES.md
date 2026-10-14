# Cases behind byline-check

Every check in byline-check comes from a case documented in published reporting. This page maps
each check to its cases and sources, so an editor can see why a line on the worksheet is there.
To add a case, open an issue or pull request with a public source.

Dates are when the case was reported. Quotes are from the linked sources.

The documented names below are also published as open data in [personas.json](personas.json)
(Apache-2.0): name, kind, what happened, month reported, sources, the outlets where the byline or expert
appeared (with web domains where a source confirms them), and who removed the work.
`python byline_check.py --cases` prints the same data.

## Checks and their cases

| Check | Case | What happened |
|---|---|---|
| Payment outside the normal system (PayPal, checks, gift cards, crypto) | WIRED, 'Margaux Blanchard' (Aug 2025) | The writer could not give enough details for WIRED's payments system and insisted on PayPal or a check. |
| Email-only contact; ask for a live call | Ottawa Citizen and Policy Options, 'Daniel Robson' (Sept 2026) | The persona said he could only communicate by email. Policy Options' editor-in-chief: "The key moment where my heart sank was when the Turkish journalist told me that Daniel Robson refused to do a video call". |
| Email-only contact | Science, impostor of Caroline Williams (Sept-Oct 2026) | Science's editors and the story's sources "had only communicated by email" with the impostor. |
| Live call that tests the writer on their own pitch | Undark (reported Oct 2026) | On a voice call a writer did not know the material in her own pitch. |
| Pitch address not listed on the writer's own site; confirm the pitch through the writer's own contact details | Science, impostor of Caroline Williams; FinanceBuzz, impostor of Ruth Jackson-Kirby (2026) | The impostors used real journalists' names and clips. A matching byline could not catch it. The Science piece ran in June 2026 and "was removed three months later, after editors discovered that the author was an impostor". FinanceBuzz's impostor pitched from an address that resembled the real writer's. |
| Quotes in the draft searched as exact phrases; confirm every quote | Science, same case | Two of the story's quotes were found in other writers' earlier stories. |
| People quoted in earlier clips, contacted by the editor | The Local (Toronto), Nov 2025 | Sources quoted in a freelancer's earlier stories said they had never spoken to her. |
| Sources in the draft or clips that match documented fake experts | 'Dr Eleni Nicolaou' and Jacob Elban (Sept 2026) | An art-therapist persona was quoted more than 30 times by outlets including Forbes, Vice, Glamour and Tom's Guide before Qwoted removed her profile; Press Gazette found she appeared to be AI-generated. |
| Annotated draft or version history | The Local, via the Reuters Institute | The Local now asks authors for annotated drafts. |
| Do not rely on AI-text detectors | WIRED, 'Margaux Blanchard' | Two AI detectors rated the fabricated feature as likely human-written. |
| Removed clips: 404, home-page redirects, editor's and removal notices, Wayback Machine copies | Business Insider, WIRED and others (2025); Ottawa Citizen and Science (2026) | Outlets removed stories and replaced them with notes, for example that a piece "didn't meet Business Insider's standards". |
| Documented persona names, for the writer and for each clip's byline and author page | OpenAI, 'Bogus Bylines' (Oct 2026); We News (Oct 2026); WIRED (2025); Ottawa Citizen (2026) | See the lists below. A clip on an outlet documented as having run that persona is called out. |
| Ask how earlier editors verified the writer | 'Bogus Bylines' (Oct 2026) | "Previous publications also became part of the personas' stated credentials." A newspaper publisher "accepted a Hoskins column because he trusted PeaceVoice, without independently verifying the author." |
| Webmail address dressed up as an organisation's | KUOW (Oct 2026) | Scammers posing as reporter Katie Campbell wrote to at least 43 book authors from Gmail addresses such as k.campbelkuow.org@gmail.com, then asked them to pay for interviews or promotional materials. At least one person paid. |
| Reply-To pointing elsewhere; SPF, DKIM and DMARC failures | General email practice | A Reply-To you have not confirmed sends your answer somewhere else. Your own mail server's authentication results show whether the sending service may use that address. |
| Young domains (RDAP) | General practice | A writer's website registered weeks ago is worth a closer look. Most real freelancers use webmail, so this check often has nothing to look at. |

## Documented personas

byline-check flags a writer's name, a clip's byline or author page, or a quoted source that
matches one of these. **Real people share these names, and several are common names.** A match
means "verify", never "fake". A name that is not on the list tells you nothing.

### Invented personas

| Byline | Case | Outlets that ran it (removed it) | Source |
|---|---|---|---|
| Margaux Blanchard | The writer could not be shown to exist (2025). | WIRED, Business Insider, SFGate, Cone Magazine, Naked Politics (all removed); Index on Censorship (investigating, Aug 2025) | [Press Gazette](https://pressgazette.co.uk/publishers/digital-journalism/margaux-blanchard-wired-ai-editors-journalist/) |
| Daniel Robson | Columns removed in Sept 2026; communicated only by email and refused a video call. | Ottawa Citizen, Montreal Gazette, Policy Options, Western Standard, The Hub, Open Canada (all removed); one piece still on Yahoo News on 29 Sept 2026 | [CBC](https://www.cbc.ca/news/canada/daniel-robson-suspected-fake-ai-persona-9.7363967), [Türkiye Today](https://www.turkiyetoday.com/world/exclusivefake-ai-columnist-dupes-canadian-press-to-target-moroccan-dissidents-and-a-t-3229120), [Press Gazette tracker](https://pressgazette.co.uk/publishers/digital-journalism/ai-journalism-mistakes/) |
| Ervin B. Hoskins | 'Bogus Bylines' (below) | Middle East Monitor (removed), PeaceVoice, Black Star News, Emmitsburg.net, Port St. Joe Star (removed), Apalachicola Times | [OpenAI](https://openai.com/index/disrupting-ai-enabled-false-front-operations/), [Marc Owen Jones](https://marcowenjones.substack.com/p/operation-bogus-bylines-the-pro-iran), [Press Gazette tracker](https://pressgazette.co.uk/publishers/digital-journalism/ai-journalism-mistakes/) |
| Noah Lamington | 'Bogus Bylines' | Asia Times, International Policy Digest | OpenAI, Marc Owen Jones |
| Sophia Gonzalez | 'Bogus Bylines' | PeaceVoice, CounterPunch, ZNetwork, News-Register, LA Progressive, Antiwar.com | OpenAI, Marc Owen Jones |
| Michael Harrison | 'Bogus Bylines' | Middle East Monitor (removed) | OpenAI, Marc Owen Jones |
| Ericka Feusier | 'Bogus Bylines' | Foreign Policy in Focus, Eurasia Review | OpenAI, Marc Owen Jones |
| Jenny Williams | 'Bogus Bylines' | Middle East Monitor (removed), NationofChange | OpenAI, Marc Owen Jones |
| Alice Johnson | 'Bogus Bylines' | Middle East Monitor (removed), Fair Observer, Libertarian Institute | OpenAI, Marc Owen Jones |
| Geneviève Tremblay, Gordon Halloway | AI-generated staff personas (a "Quebec correspondent" and an editor-in-chief) of the We News site, which labels its staff profiles as AI-generated. | We News | [Canadian Press](https://www.cp24.com/news/canada/2026/10/03/byline-or-bot-ai-generated-journalists-start-to-appear-in-canada/) |

'Bogus Bylines': OpenAI reported on 8 Oct 2026 that almost 100 articles ran under seven fake
bylines in about a dozen outlets between July 2025 and October 2026, mostly about the US-Iran
conflict. The operators used ChatGPT to fit drafts to outlets' submission rules and to write pitch
emails. OpenAI could not identify who was behind it and said it looked like a campaign for hire.
Marc Owen Jones traced the articles across 17 sites; Modern Diplomacy is among them, with no
persona named, so it is not attached to a byline here. Middle East Monitor told the Washington Post
it had removed the affected articles, and PeaceVoice said it had strengthened its policy against
AI. "Removed" above means a source reported the removal; the rest were not reported as removed
when the sources were published.

### Real writers who were impersonated

These are real journalists. The worksheet tells you to reach them through contact details you
find yourself and ask them to confirm the pitch. Their own clips are not flagged.

| Name | Case | Source |
|---|---|---|
| Caroline Williams | Science journalist. An impostor used her name and clips to sell Science a story in June 2026 (removed in Sept), then pitched Science and Knowable again. | [CJR, 8 Oct 2026](https://www.cjr.org/analysis/fake-caroline-williams-science-nature-magazine-ai-influx-pitches.php) |
| Katie Campbell | KUOW reporter. Scammers used her name and lookalike Gmail addresses to email book authors, then asked them to pay for interviews. | [KUOW, 12 Oct 2026](https://kuow.org/technology/2026-10-12/scammers-used-ai-to-impersonate-me-a-kuow-reporter-heres-how-to-avoid-such-traps) |
| Ruth Jackson-Kirby | UK personal-finance journalist. An impostor pitched FinanceBuzz from an address resembling hers; FinanceBuzz ran articles under her name with an author page showing an AI photo, then took them down when she objected. | [Press Gazette tracker](https://pressgazette.co.uk/publishers/digital-journalism/ai-journalism-mistakes/) |

### Invented experts quoted as sources

| Name | Case | Source |
|---|---|---|
| Eleni Nicolaou ('Dr Eleni Nicolaou') | Billed as an art therapist, clinical psychologist or psychiatrist; quoted more than 30 times in 2026 by Tom's Guide, Forbes, Glamour, Vice, Netmums, AOL, Yahoo, Parade and others. The Art Therapy Credentials Board had no record of her. Qwoted removed her profile. | [Press Gazette, 18 Sept 2026](https://pressgazette.co.uk/news/prominent-art-therapist-quoted-by-vice-forbes-and-others-is-ai-generated/) |
| Jacob Elban | A "business expert" offered by the same company. Qwoted and Pressflow removed his profile. | Same |

## What the list leaves out, and why

- Business Insider removed about 40 personal essays under more than a dozen bylines in 2025 as not
  meeting its standards. Some of those bylines may belong to real people, so they are not listed by
  name. The removal-notice check covers those pages.
- Bylines that are only accused, without a publisher or platform finding, are left out.
- Cleveland.com put a real reporter's byline on an AI-assisted story she had not worked on (Sept
  2026). That was the outlet's own error, not an impostor, so it is not listed.
- Brown Brothers Media's sites ran AI articles under made-up bylines, but the reporting names no
  individual bylines.

## Further reading

- Press Gazette's running tracker of AI-related journalism cases:
  https://pressgazette.co.uk/publishers/digital-journalism/ai-journalism-mistakes/
- Reuters Institute, "Speed, hoaxes and mistrust: How AI is transforming freelance journalism":
  https://reutersinstitute.politics.ox.ac.uk/news/speed-hoaxes-and-mistrust-how-ai-transforming-freelance-journalism

Made by MV2 of Munim, Inc., with AI agents working in his name. Corrections are welcome:
munimversion2@gmail.com.
