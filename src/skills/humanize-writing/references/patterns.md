# Pattern catalog

The 39 AI-writing patterns this skill removes, numbered for reference. Each entry: what it is, why it reads as machine output, and one before/after pair. The source is Wikipedia's "Signs of AI writing" (WikiProject AI Cleanup), checked against the page as of September 2026, plus the corpus studies that page cites (Kobak et al. 2025 in *Science Advances*; Juzek & Ward 2025; Reinhart et al. 2025 in *PNAS*; Russell et al. 2025).

Two things to hold in mind while reading:

**Density is what matters.** One pattern in a page of text is noise; five in a paragraph is a signature. Wikipedia is explicit that these are *signs*, not proof, and that humans use every one of them sometimes.

**The underlying mechanism is regression to the mean.** Wikipedia's description: a language model tends toward "the most statistically likely result that applies to the widest variety of cases", so it drops the specific, unusual fact and replaces it with a generic, positive one. Its example: the highly specific "inventor of the first train-coupling device" becomes "a revolutionary titan of industry". The subject gets less specific and more exaggerated at the same time. Almost every pattern below is a symptom of that one move, and the fix is always the same in spirit: put the specific back and take the exaggeration out.

**About the examples.** Every "after" below uses only information that was already in the "before". That is deliberate. Humanizing a text means recovering the facts the AI phrasing buried, never inventing new ones to sound concrete. Where the "before" contains no fact at all, the honest "after" is a cut.

## A. Sentence structure

### P1. Negative parallelism

"It's not X, it's Y", "not just X but Y", and the two-sentence cousin ("This isn't about speed. It's about trust."). Wikipedia's description of why it reads as machine output is useful: the text behaves "as though it is clearing up a common misconception", correcting a wrong idea the reader never had. The same reflex produces sentences that answer objections nobody raised ("This isn't mainly about cost...") and the reversed form "X rather than Y" (which Wikipedia notes is especially common in Grok output). State the positive claim and let it stand.

- Before: *The library isn't just a place to borrow books. It's a community hub that hosts a weekly homework club and a Saturday repair café.*
- After: *The library lends books and hosts a weekly homework club and a Saturday repair café.*

### P2. Correlative "not only... but also"

Same reflex in formal dress. Almost always deletable without losing meaning.

- Before: *The new bus route not only shortens the trip to the hospital but also runs every fifteen minutes.*
- After: *The new bus route shortens the trip to the hospital and runs every fifteen minutes.*

### P3. Rule of three

Triplet adjectives, triplet benefits, triplet examples, everywhere. Wikipedia notes LLMs use the triplet "to make superficial analyses appear more comprehensive". Usually two of the three items carry no information. Keep the one that does; if a list honestly has four items, keep four.

- Before: *The clinic offers fast, friendly, and professional care, with same-day appointments for children under five.*
- After: *The clinic gives same-day appointments to children under five.*

### P4. False ranges

"From X to Y" implying a spectrum that doesn't exist. Name the actual things.

- Before: *The eight-week course covers everything from basic knife skills to advanced pastry: knife work, stocks and sauces, bread, and laminated dough.*
- After: *The eight-week course covers knife work, stocks and sauces, bread, and laminated dough.*

### P5. Significance-laden trailing participles

A sentence states a fact, then a participle clause editorializes about what it shows: "reflecting...", "highlighting...", "underscoring...", "ensuring...", "contributing to...", "fostering...", "symbolizing...". Wikipedia files this under "superficial analyses": the clause is the model's own opinion attached to a fact, and in newer models it is often attributed to a named source that said nothing of the kind. State the fact and stop.

- Before: *The station added a second platform in 1998, reflecting its growing importance to the regional network.*
- After: *The station added a second platform in 1998.*

### P6. Copula avoidance

"Serves as", "stands as", "functions as", "represents", "marks", "boasts", "features", "offers" for plain "is" and "has". Wikipedia cites a measured drop of over 10% in "is"/"are" in academic writing in 2023 and notes the newer, longer forms: "ventured into politics as a candidate" for "was a candidate", "began his career as" for "was". Also "refers to" in an opening sentence, which describes the term instead of the thing.

- Before: *The hall serves as the village's polling station and boasts seating for 120.*
- After: *The hall is the village's polling station and seats 120.*

### P7. Synonym cycling

Rotating through "the bakery / the shop / the business / the establishment" to avoid repeating a word. Wikipedia now lists this under *historical* indicators (older models had a repetition penalty), so it is a weaker signal for 2025+ output, but it still reads badly. Humans repeat names.

- Before: *The bakery opened in 2011. The shop added a second oven in 2015. The business now employs 14 people, and the family-run establishment is closed on Mondays.*
- After: *The bakery opened in 2011 and added a second oven in 2015. It now employs 14 people and is closed on Mondays.*

### P8. Staccato manufactured-drama fragments

Chains of punchy fragments engineered for gravitas. One deliberate fragment lands; three in a row is a formula.

- Before: *One river. Three bridges. Zero closures in forty years.*
- After: *The river's three bridges have not been closed in forty years.*

### P9. Hedging stacks

Two or more hedges guarding one claim ("could potentially help in some cases"). Note the distinction Wikipedia draws: a single hedge or intensifier ("perhaps", "tends to", "very") is a sign of *human* writing. The stack is the tell. Pick one confidence level.

- Before: *The change could potentially help reduce waiting times in some cases.*
- After: *The change may reduce waiting times.*

### P10. Wordy constructions (a concision choice, not an AI sign)

"In order to", "due to the fact that", "the process of". Trim them when the register wants tight prose. But be clear about what this is: Wikipedia lists "in order to" and "the fact that" among the constructions *more* common in human writing than in AI output. Cutting them makes text shorter, not more human, and the linter no longer flags them.

- Before: *In order to renew a permit, residents need to bring proof of address.*
- After: *To renew a permit, residents need proof of address.*

### P11. Uniform sentence rhythm

Three or more consecutive sentences of the same length and shape. Human prose varies; follow a long sentence with a short one.

- Before: *The museum opens at ten. The café opens at eleven. The shop closes at five.*
- After: *The museum opens at ten and the café an hour later; the shop closes at five.*

### P12. Echo restatement

The same point re-said in slightly different words within a paragraph. Say it once.

- Before: *The pool closes for maintenance in March. During March the pool will not be open. Swimmers should expect the facility to be unavailable that month.*
- After: *The pool closes for maintenance in March.*

## B. Framing and claims

### P13. Compulsive summaries

"In conclusion", "Overall", "In summary", "Ultimately", or a closing paragraph that restates the piece. Wikipedia lists section summaries under historical indicators (strongest in 2023-era output) but they still appear. End on your last substantive point.

- Before: *The committee recommended Mill Road, the only site on a bus route. In conclusion, after weighing cost against access across three sites, Mill Road emerged as the committee's recommendation.*
- After: *The committee recommended Mill Road, the only site on a bus route.*

### P14. Editorializing filler

"It's important to note that", "It's worth mentioning", "It is crucial to remember", "Notably", "Interestingly". Wikipedia calls these "didactic disclaimers" and dates them to 2022–2024 output; newer models do it less, but it is still a cut. If the thing is important, saying it is enough.

- Before: *It's important to note that the footpath is closed until April.*
- After: *The footpath is closed until April.*

### P15. Vague attribution

"Experts say", "studies show", "observers have cited", "industry reports suggest", "described in scholarship", with no named source. Wikipedia's page also flags inflating the count: "several publications" when one is cited, "such as" before a list that is actually exhaustive. Name the source or own the claim yourself.

- Before: *Experts agree the bridge needs repairs. According to industry reports, including the council's 2024 inspection, the cost could exceed £2 million.*
- After: *The council's 2024 inspection found the bridge needs repairs costing over £2 million.*

### P16. Overgeneralization

One or two sources presented as consensus: "widely regarded as", "commonly considered". Claim exactly what your sources support.

- Before: *The method is widely regarded as the standard approach; a 2019 review in the Journal of Hydrology recommended it.*
- After: *A 2019 review in the Journal of Hydrology recommended the method.*

### P17. Undue significance and legacy framing

"Pivotal moment", "enduring legacy", "setting the stage for", "key turning point", "indelible mark", "deeply rooted", "reflects broader trends", "generated debate", "prompted broader reflection". Importance asserted rather than shown. Wikipedia notes models do this even for etymology and population figures, and sometimes add a preamble admitting the subject is minor before insisting on its importance anyway.

- Before: *The bypass opened in 2003, marking a pivotal moment in the town's history and setting the stage for decades of growth.*
- After: *The bypass opened in 2003.*

### P18. Promotional puffery

"Vibrant", "nestled", "renowned", "rich heritage", "breathtaking", "commitment to", "exemplifies", "state-of-the-art". Brochure language. Wikipedia notes that newer models are subtler: they avoid "the best" but still lean positive. Describe what the thing does. An unnamed award is a claim with no content; name it or cut it.

- Before: *Nestled in the heart of the Peak District, the award-winning inn boasts a rich heritage dating to 1780.*
- After: *The inn is in the Peak District and dates to 1780.*

### P19. Formulaic challenges-and-outlook sections

"Despite these challenges, X continues to..." followed by a speculative bright future. Wikipedia: the sign is the rigid formula, not any mention of a challenge. Real analysis names specific obstacles and specific plans; if there are none, end on the last fact.

- Before: *Membership fell from 40 to 26 after the hall closed. Despite these challenges, the choir remains well-positioned for growth as the community continues to evolve.*
- After: *Membership fell from 40 to 26 after the hall closed.*

### P20. Definition, restatement, and announcement openers

Opening by defining the topic ("Composting is the process by which..."), restating the prompt, treating the title as a proper noun ("The list of X is a curated compilation of..."), or announcing what is about to be said ("Let's dive into...", "Here's what you need to know"). Open with the most useful true thing.

- Before: *Composting is the natural process by which organic waste breaks down into soil. Let's dive into how to get started. A bin needs roughly equal amounts of green and brown waste and a turn every two weeks.*
- After: *A compost bin needs roughly equal amounts of green and brown waste and a turn every two weeks.*

## C. Conversational artifacts

Chatbot-to-user language that leaks into deliverables. Wikipedia's words to watch: "I hope this helps", "Of course!", "Certainly!", "You're absolutely right!", "Would you like...", "is there anything else", "let me know", "more detailed breakdown", "here is a...". All of these must be stripped from any text meant to stand alone.

### P21. Sycophantic openers

- Before: *Great question! You're absolutely right that drainage matters. Clay soil holds water for days after rain.*
- After: *Clay soil holds water for days after rain.*

### P22. Fake-candid openers

"Honestly?", "Let's be real:", "Here's the thing:" as a staged pause before an ordinary claim. (The words are fine mid-sentence in casual writing; the tell is the theatrical standalone opener.)

- Before: *Honestly? Here's the thing: most seedlings die from overwatering.*
- After: *Most seedlings die from overwatering.*

### P23. Chatbot closers

- Before: *...and the hall is booked for 14 June. I hope this helps! Let me know if you need anything else.*
- After: *...and the hall is booked for 14 June.*

### P24. Collaborative offers

- Before: *[end of a newsletter] Would you like me to also draft the volunteer sign-up form?*
- After: *[nothing after the final substantive sentence]*

### P25. Knowledge-cutoff disclaimers and speculative gap-filling

"As of my last update..." is the old form. Wikipedia documents the newer one: a model that cannot find a fact says so ("specific details are not widely documented", "based on available information") and then fills the gap with a guess ("she likely grew up locally", "maintains a low profile"). Both the disclaimer and the guess are fabrication. Cut them; if a source gives the fact, state it.

- Before: *While specific details about the founder's early life are not widely documented, she likely grew up locally and maintains a low profile.*
- After: *[cut. If a source gives her birthplace, state it; otherwise say nothing about her early life.]*

### P26. Placeholder text

"[Insert company name]", "[date]", "PASTE_URL_HERE": unfilled template slots shipped as finished text.

- Before: *Join us on [date] at [venue] for the annual plant sale.*
- After: *Join us on 4 May at the village hall for the annual plant sale.* (The date and venue come from the writer. If you don't have them, ask; never guess.)

## D. Formatting

### P27. Em dash overuse

Humans use em dashes; AI uses them more often than non-professional writers of the same genre, and in places where commas, parentheses, or colons belong. Two details from Wikipedia worth knowing: AI em dashes are usually *spaced* (" — "), against typographic convention; and by 2026 the habit varies by model, with GPT-5.1 trained to suppress them and Claude still using them more than professional writers do (Economist, July 2026). Hard limit here: one per ~300 words, unspaced, and only where a comma genuinely wouldn't work.

- Before: *The ferry — which runs hourly — stops at two islands — Bryher and Tresco — in summer.*
- After: *The ferry runs hourly in summer and stops at Bryher and Tresco.*

### P28. Bold mid-sentence emphasis

Bolding key terms mid-prose in a "key takeaways" fashion, often every instance of a chosen word. Bold is for structure the reader navigates by.

- Before: *Bring **photo ID**, **proof of address**, and your **old permit**.*
- After: *Bring photo ID, proof of address, and your old permit.*

### P29. "Term: definition" bullets

The bolded-label-colon-description list (Wikipedia: "inline-header vertical lists"), AI's favorite way to fake structure.

- Before: *- **Parking:** free after 6pm. - **Access:** step-free from the north entrance.*
- After: *Parking is free after 6pm, and there is step-free access from the north entrance.*

### P30. List compulsion

Bullets or numbered lists where a sentence would do. Default to prose; use a list only when the user asks or the content is truly enumerable (steps, specs, options).

- Before: *What to bring: • water • a sun hat • the signed form*
- After: *Bring water, a sun hat, and the signed form.*

### P31. Emoji as formatting

Emoji in headings or as bullet markers. Wikipedia notes this is rarer in 2026 output than it was, but it still appears. Never in headings.

- Before: *## 🌱 Spring planting*
- After: *## Spring planting*

### P32. Title-case headings

Capitalizing Every Main Word In Headings. Use sentence case unless the user's style guide requires otherwise.

- Before: *## How To Register Your Allotment*
- After: *## How to register your allotment*

### P33. Section-skeleton overkill

Headings on short content; a rigid Introduction / Challenges / Future Outlook / Conclusion scaffold; a title heading that repeats the document's name; headings that contain only other headings and no text; "X and Y" headings ("Awards and recognition" is near-ubiquitous in AI articles); horizontal rules between every section; skipped heading levels. No headings under ~400 words. Let the material dictate structure.

- Before: *[A 250-word notice with a title heading repeating the document name, then "Introduction", "Key Details", "Awards and Recognition", "Conclusion", separated by horizontal rules]*
- After: *[the same 250 words as two paragraphs]*

### P34. Curly and straight quote mix

Both "smart" and "straight" quotation marks (or apostrophes) in one document: the fingerprint of AI text pasted into hand-typed text. Wikipedia's note on who does what: ChatGPT and DeepSeek typically emit curly quotes; Gemini and Claude typically don't; word processors auto-curl. Curly quotes alone prove nothing. Mixing is the tell; pick one and be consistent.

- Before: *The sign says “no dogs” but the leaflet says "dogs on leads".*
- After: *The sign says "no dogs" but the leaflet says "dogs on leads".*

## E. Vocabulary

### P35. AI-vocabulary hits

Words measured to spike after 2022. Wikipedia's current list: *additionally* (sentence-initial), *align with*, *boasts*, *bolstered*, *crucial*, *deep dive*, *delve*, *emphasizing*, *enduring*, *enhance*, *fostering*, *garner*, *highlight* (verb), *interplay*, *intricate*, *key* (adjective), *landscape* (abstract), *meticulous*, *pivotal*, *robust*, *showcase*, *tapestry*, *testament*, *underscore*, *valuable*, *vibrant*. The list shifts by model generation (see `vocabulary.md`), and Wikipedia warns to take it literally: a word's synonyms are not also suspect. Full list with replacements in `vocabulary.md`.

- Before: *The festival showcases a vibrant tapestry of local cheeses, ciders, and breads, underscoring the region's rich culinary heritage.*
- After: *Local cheese, cider, and bread are the focus of the festival.*

### P36. Stock idioms and manufactured aphorisms

"At the end of the day", "in today's fast-paced world", "a testament to", and the coined-proverb form "X is the language of Y" / "X is the currency of Z". Prefab phrases that sound like insight and carry none. Replace with the specific claim, or cut.

- Before: *At the end of the day, in today's fast-paced world, a good night's sleep is a testament to good habits.*
- After: *People with regular habits sleep better.*

## F. Newer patterns (2025 onward)

Wikipedia flags these as more common in text from models released in 2025 or later.

### P37. Canned notability and media-coverage claims

Proving a subject matters by describing the *sources* that covered it: "featured in national media outlets", "independent coverage", "trade publications", "written by a leading expert", "maintains an active social media presence". Wikipedia notes the wording often echoes Wikipedia's own notability guidelines, as if the model collapsed the article and its justification. Say what the coverage actually said, or cut the sentence.

- Before: *She has been featured in national media outlets including the BBC and The Guardian, and maintains an active social media presence.*
- After: *The BBC and The Guardian have covered her work.*

### P38. Vague connection and association

"In connection with", "associated with", "in association with", "connected to" used to gesture at a relationship instead of naming it: member of, founded, taught, caused by, used for. One is fine; a paragraph of them means the model didn't know the relationship and is hiding it.

- Before: *He is associated with the Riverside Orchestra, which he founded in 1994, and later became connected with music education in Hull.*
- After: *He founded the Riverside Orchestra in 1994 and later taught music in Hull.*

### P39. Unnecessary small tables

A two- or three-row table for facts that belong in a sentence. Wikipedia lists this as rare but distinctive. Tables are for data a reader compares across rows.

- Before: *[A table: "Founded | 1911" / "Members | 240"]*
- After: *The club was founded in 1911 and has 240 members.*

## Signs of human writing

Wikipedia keeps a short list of constructions that are *more* common in human-written text than in AI output. In generation mode these are permission slips; in rewrite mode, leave them alone when you find them.

- Simple "is"/"has" phrases: "there is a", "it has a".
- Plain verbs where a stiffer synonym exists: *wrote* (not authored), *moved* (not relocated), *used* (not utilized), *tried* (not attempted), *died* (not passed away).
- Definite, superlative statements when they are true: "was the first", "is the only", "one of the best". Newer models hedge these away.
- A single hedge or intensifier: "very", "perhaps", "tends to".
- Ordinary wordiness: "as a result of", "in order to", "the fact that".
- Specific, odd, unglamorous details; mixed feelings; parenthetical asides and self-corrections; uneven sentence lengths. These are exactly what regression to the mean removes.

## What is *not* a sign

Also from Wikipedia, for the false-positive guard: perfect grammar; a mix of casual and formal register; prose that merely feels "bland" or "robotic"; formal or academic vocabulary in general (only the specific words above are measured); a single transition word; unsourced claims; curly quotes on their own; em dashes on their own. None of these should trigger a rewrite.
