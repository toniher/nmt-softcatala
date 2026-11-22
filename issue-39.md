# Issue #39 — characters the models can't represent get mangled (all pairs)

https://github.com/Softcatala/nmt-softcatala/issues/39 (open since 2026-04-29). A user translating
reStructuredText docs in PO files: `` ``ubports/24.6.x`` `` → `theubports/24.6.x.` and
`24.6.x_-_PR_morph-browser_125` → `an24.6.x-PRmorph-browser125..` (eng-cat). The issue is
reported for one pair, but it affects every model.

## Context: what is going on (verified in this session)

The issue output was reproduced exactly with `eng-cat` + current code. API, `model_to_txt` and
`model_to_po` all go through `CTranslate.translate_parallel` (`use-models-tools/nmt_sc/ctranslate.py`).

### Cause 1 — every model has characters it cannot represent
Each SentencePiece model (`tokenizer/sp_m.model`, AINA `spm.model`) maps some characters to
`<unk>`. This was checked for all 22 published Softcatalà models (tokenizer fetched with HTTP range
reads) and all 12 AINA models.

| Models | Unknown ASCII |
|---|---|
| eng-cat, cat-eng | ``# < = > @ ^ _ ` \| ~`` |
| eus-cat, cat-eus | ``# $ & * + < = > @ \ ^ _ ` { \| } ~`` |
| deu, fra, ita ↔ cat | ``# $ * + @ \ ^ ` { \| } ~`` (deu also `[ ]`) |
| nld, por ↔ cat | as deu, plus `!` (por also `& < = > _`) |
| spa ↔ cat | ``! # $ & * + @ [ \ ] ^ ` \| }`` |
| jpn ↔ cat | ``@ \ ^ ` { \| }`` |
| glg ↔ cat | `^ ~` |
| oci ↔ cat | `~` |
| AINA (all 12) | 8–17 of the above each, always including ``< \ ^ ` { }`` |

Non-ASCII characters are unknown almost everywhere: `€ £ § ¡` in all models; `° ¿` in most;
`‘ ’ “ ” —` in many (deu, nld, por, spa, eus…).

Origin, upstream in training: the corpus scripts (`data-processing-tools/po-to-text.py`
`_remove_accelerators`, `clean-text-file.py`) strip `_ & ~` and HTML tags. The other characters
are presumably too rare to make SentencePiece's character coverage.

### Cause 2 — `replace_unknowns=True` produces garbage
`_translate_batch` replaces each output `<unk>` with the source token that had the most attention,
which often isn't the unknown character. Measured with the current code:

| Model | Input | Output |
|---|---|---|
| eng-cat | `It costs 20 € and the temperature is 30 °C.` | `Costa 20  and i la temperatura és de 30  theC.` |
| eng-cat | `Use a \| b to pipe the output.` | `Utilitzeu a . b …` |
| eng-cat | `Set my_variable_name to true.` | `Estableix el meuvarivariable.nom a cert.` |
| eus-cat | `Prezioa 20 $ da & beste * bat.` | `El preu és de 20 . . un altre ..` |
| eus-cat | `…info@example.com…` | `info.example.com` |

### Cause 3 — `model_to_po._clean_string` deletes every `_ & ~`
It does this to drop UI accelerators (`_File`, `&Open`, `~Save`), but it also deletes them from
identifiers in documentation PO files. That is the "underscore deleted" part of the issue.

### Cause 4 — the HTML-tag marker itself is unknown on most models
`PreserveMarkup` swaps tags for `{87719<n>`, but `{` is unknown in 9 of 11 Softcatalà source
languages and in every AINA model. Only eng, glg, oci and spa sources are safe.
For example, eus-cat: `Egin klik <b>Gorde</b> botoian.` → `Feu clic a 87877190 Desa 87877191.`
(tags lost). Production has this bug too.

### Fork vs upstream
This repo is the `toniher/nmt-softcatala` fork. `preservemarkup.py` and
`sentencepiecetokenizer.py` are identical to upstream, and `ctranslate.py` differs only in
env-var reading, so one patch serves both.

## Status (2026-11-22)

Fix A is implemented in this fork (uncommitted at the time of writing). Measured on all 22 published
Softcatalà models and 3 AINA models, with a per-source-language test set (code spans, identifiers,
email, `€ °C >= | ~ ^`, an HTML tag sentence, plus 3 ordinary sentences each):

| | old code | new code |
|---|---|---|
| Protected text kept verbatim, Softcatalà (22 pairs) | 57/209 | 200/209 |
| Protected text kept verbatim, AINA (eng-cat, cat-eng, deu-cat) | 30/32 | 32/32 |
| Ordinary sentences with identical output | — | 75/75 |

The 9 remaining misses are characters the model knows but drops by itself (`|` in cat-glg and
cat-oci; `_` and `>=` in jpn models), plus cat-jpn, whose output is poor overall.
Marker choice measured: `{87719<n>` where the model knows `{`, else `87719<n>`. The digits-only
form beat `(`, `%`, `/`, `XYZ` and `0x` prefixes on the 14 models lacking `{` (124/131 kept).

Found on the way and fixed separately on `master` (c7c4ab3, merged into this branch): the AINA
`es-ca` / `ca-es` repos ship `shared_vocabulary.txt` and no `config.json`, which
`download-aina-models.sh` could not install. It now uses whichever of the known files a repo has.

## Fix A — inference side, `use-models-tools/nmt_sc` (no retraining)

Principle: a sentence with no unknown characters, no code spans and no tags is tokenized exactly
as today, so its translation can't change. Only the problem sentences are touched.

1. **Detect per model, per input** (`sentencepiecetokenizer.py`): add `is_unknown(char)`
   (`unk_id()` in `encode("a"+c+"a")`, memoized). Characters are taken from the input itself, so
   non-ASCII ones are covered as well, with no hard-coded list.
2. **Normalize when there is a safe equivalent** (`ctranslate.py`, generalize
   `_normalize_input_string`, which today only maps `’`→`'` for Catalan sources). If the model
   doesn't know a character, map it:
   - `’ ‘` → `'`
   - `“ ”` → `"`
   - `—` → `-`
   - `…` → `...`
   - `¿ ¡` → removed; the targets don't use them, and cat-eng already drops them.

   Otherwise `L’ordinador` would get protected as a whole word and left untranslated.
3. **Protect the rest** (`preservemarkup.py`, `PreserveMarkup(is_unknown)`), scanning with
   `re.finditer` over the original text:
   - HTML tags `<…>`: each tag separately, as today, so the text between them is still
     translated;
   - inline code ``` ``…`` ``` and `` `…` ``: the whole span;
   - identifier-like tokens: a run of non-space characters containing an unknown character and
     at least one letter or digit (`my_variable_name`, `user@example.com`,
     `24.6.x_-_PR_morph-browser_125`, `20€`). Trailing `.,;:!?)` stays outside the marker;
   - standalone runs of unknown characters (`€`, `°`, `|`, `>=`, `$`, `&`, `*`): only the run.
4. **Marker made only of characters the model knows** (fixes cause 4). Choose the form
   empirically: candidates are tested through every model, and the one that round-trips
   everywhere wins. If no single form works for all models, pick one per model from the
   candidates at load time with `is_unknown`.
5. **`model_to_po._clean_string`**: strip `_ & ~` only where it is an accelerator: at the start
   of the string or after whitespace, directly before a letter, and outside backtick spans.
6. Keep `replace_unknowns=True` as the last resort for anything left over.

### Tests (`make run-tests`; `tests/data` has the eng-cat and cat-eng SP models)
- `testsentencepiecetokenizer.py`: `is_unknown` returns true for `` _ ` @ € `` and false for
  letters, digits and `.`.
- `testpreservemarkup.py`: existing cases unchanged, plus:
  - the issue sentence;
  - `` `foo` ``;
  - an identifier;
  - an email followed by a dot;
  - `x >= 3`;
  - `20 €`;
  - `<b>Save</b>`, where the text between the tags is still exposed;
  - round trip through `get_back_markup`.
- `ctranslate` normalization: `’ “ ” — … ¿ ¡` handled only when unknown to the model.
- `_clean_string`: `_File`, `&Open`, `~Save` are stripped; `my_var`, `24.6.x_-_PR`,
  `` ``a_b`` `` and `Tom & Jerry` are kept.
- `serving/translate-service/api-tst/test-apertium.py`: the issue sentence through `/translate`.
  Assert the three spans appear verbatim, not the exact wording, which changes between model
  and CTranslate2 versions.

## Fix B — upstream

1. **Softcatala/nmt-softcatala**: Fix A as a PR referencing #39, with the per-pair table above and
   the tag-marker bug (cause 4). It should rebase cleanly.
2. **Softcatala/nmt-models**, the long-term fix (needs retraining, not this PR): open an issue to
   - remove `_ & ~` only as accelerators in `po-to-text.py` and `clean-text-file.py`;
   - train SentencePiece with `byte_fallback=True` (or `user_defined_symbols`) so no character
     is unknown.
   Then Fix A becomes a no-op for new models. Code-span protection is still worth keeping.
   Same report for Projecte Aina if they are interested. Also note that cat-spa cannot output
   `¿ ¡` at all, which a Spanish target needs.
3. Comment on #39 with the diagnosis and a link to the PR.

## Verification

1. `make run-tests`: all suites pass.
2. **Every pair, before and after.** Download all Softcatalà models into a scratch `MODELS_DIR`
   (`make download-models`), plus a few AINA ones. Build a small corpus per source language:
   - the issue sentence;
   - an identifier, an email and a code span;
   - `€ ° § | $ & *`, typographic quotes and apostrophes, `¿ ¡` for Spanish;
   - an HTML tag sentence;
   - 3 ordinary sentences.

   Run it through `translate_parallel` with the old and the new code, then check that:
   - ordinary sentences give identical output;
   - protected spans come back verbatim;
   - tags survive on every model, eus-cat, deu-cat and AINA included.
3. `model_to_po` on a small PO with the issue msgid plus `_File` / `&Open`.
4. Build the images and run `make docker-run-translate-service-test` (the existing 13 tests
   plus the new one).
