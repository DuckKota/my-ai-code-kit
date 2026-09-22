---
name: humanizer
description: Humanize text — strip AI-writing patterns from pasted text or a file without changing what it says
argument-hint: "[text to humanize, or a file path]"
---

Humanize the text below (or the file it names) using the humanize-writing skill in **rewrite mode**.

If the humanize-writing skill is installed, load it now and follow it in full, including `references/patterns.md` and `references/vocabulary.md`. If it is not available, apply the rules summarized here.

## Input

$ARGUMENTS

If the input is a file path, read the file and rewrite only its prose: leave code blocks, front matter, data, and link targets untouched, then write the result back to the same file. If the input is empty, ask the user to paste the text or give a file path. Do nothing else.

## Rules (rewrite mode)

Preserve everything except the patterns:

- Never alter direct quotes; quoted third-party text stays verbatim.
- Never change citations, numbers, statistics, dates, URLs, or proper nouns.
- Keep every claim the text makes. Change phrasing, not meaning.
- **Never add a fact, name, number, date, quote, or citation that is not in the source.** If a sentence needs a specific you don't have, leave the sentence plainer rather than invent one.
- Detect the register (social / email / editorial / formal) and keep it. Contractions and fragments are fine in a post; neither belongs in a formal report.
- If a `voice-profile.md` exists in the project, match it.

Strip, in order of damage:

1. Negative parallelism: "It's not X, it's Y", "not only X but also Y", "X rather than Y". State the positive claim.
2. Trailing significance clauses: "..., reflecting / highlighting / underscoring / ensuring / contributing to ...". State the fact and stop.
3. Significance inflation and puffery: pivotal moment, enduring legacy, setting the stage for, testament to, nestled, vibrant, renowned, rich heritage.
4. AI vocabulary: delve, tapestry, intricate, interplay, crucial, pivotal, key (adj.), leverage, robust, seamless, foster, enhance, align with, showcase, underscore, empower, streamline, holistic, comprehensive, transformative, cutting-edge, game-changer, myriad, plethora, deep dive, ever-evolving.
5. Copula avoidance: "serves as", "stands as", "boasts", "features", "offers" → "is", "has".
6. Rule of three: keep the item that carries information; drop the padding.
7. Vague attribution and canned coverage: "experts say", "studies show", "featured in national media outlets", "maintains an active social media presence". Name the source or cut.
8. Vague association: "associated with", "in connection with" → the actual relationship (founded, taught, member of).
9. Summary closers ("In conclusion", "Overall", "Ultimately"), editorializing ("It's important to note"), challenges-and-outlook endings. End on the last substantive point.
10. Chatbot residue: "Great question", "You're absolutely right", "I hope this helps", "Let me know if", "Would you like me to", "As of my last update", "While specific details are not widely documented" followed by a guess. Delete.
11. Formatting: at most one em dash per ~300 words and unspaced; no bold mid-sentence; no `**Term:** definition` bullets; no emoji in headings; sentence-case headings; no headings under ~400 words; consistent quotation marks; no two-row tables.
12. Rhythm: vary sentence length; say each idea once.

Do not "fix" ordinary wordiness such as "in order to" or "the fact that"; Wikipedia lists those as signs of human writing.

## Output

Return only the humanized text. No preamble, no list of changes, no closing offer. If you edited a file, say which file and stop.
