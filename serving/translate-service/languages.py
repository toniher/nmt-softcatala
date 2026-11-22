# -*- encoding: utf-8 -*-
"""Language codes and names used by the API. Import-light so it is unit-testable without Flask."""

# ISO 639-3 code -> (ISO 639-1 code, English name, Catalan name)
LANGUAGES = {
    "cat": ("ca", "Catalan", "català"),
    "deu": ("de", "German", "alemany"),
    "eng": ("en", "English", "anglès"),
    "eus": ("eu", "Basque", "basc"),
    "fra": ("fr", "French", "francès"),
    "glg": ("gl", "Galician", "gallec"),
    "ita": ("it", "Italian", "italià"),
    "jpn": ("ja", "Japanese", "japonès"),
    "nld": ("nl", "Dutch", "neerlandès"),
    "oci": ("oc", "Occitan", "occità"),
    "por": ("pt", "Portuguese", "portuguès"),
    "spa": ("es", "Spanish", "castellà"),
}

_TO_ISO639_3 = {two: three for three, (two, _, _) in LANGUAGES.items()}


def langpair_to_iso639_3(langpair):
    """Apertium 'en|ca' (2- or 3-letter codes) -> internal 'eng-cat' key."""
    return "-".join(_TO_ISO639_3.get(code, code) for code in langpair.split("|"))


def language_name(code, locale="en"):
    """Name of an ISO 639-3 code in Catalan (locale starting with 'ca') or English; None if unknown."""
    if code not in LANGUAGES:
        return None
    _, english, catalan = LANGUAGES[code]
    return catalan if locale.startswith("ca") else english
