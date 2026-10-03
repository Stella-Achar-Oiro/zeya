"""
Test messages for the danger-sign gate.

``PATTERN_EXAMPLES`` has one message per pattern in ``DANGER_SIGN_PATTERNS``, in
order: (category, pattern index within category, message). Each message matches
its target pattern and no earlier pattern in the same category, so the matched
keyword proves that particular pattern fired.
"""

PATTERN_EXAMPLES: list[tuple[str, int, str]] = [
    ("bleeding", 0, "I am bleeding since morning"),
    ("bleeding", 1, "there is excessive blood on my clothes"),
    ("bleeding", 2, "I passed a blood clot"),
    ("bleeding", 3, "naendelea kutoka damu"),
    ("bleeding", 4, "kuna damu nyingi"),
    ("headache_vision", 0, "I have a severe headache"),
    ("headache_vision", 1, "I have blurred vision"),
    ("headache_vision", 2, "my vision is blurred"),
    ("headache_vision", 3, "I keep seeing stars"),
    ("headache_vision", 4, "nina kichwa kuuma"),
    ("headache_vision", 5, "macho kuona vibaya leo"),
    ("fever", 0, "I have a high fever"),
    ("fever", 1, "a severe fever since yesterday"),
    ("fever", 2, "I have chills"),
    ("fever", 3, "nina homa kali"),
    ("fever", 4, "nasikia baridi mwilini"),
    ("fetal_movement", 0, "reduced fetal movement today"),
    ("fetal_movement", 1, "no fetal movement since last night"),
    ("fetal_movement", 2, "the baby isnt moving"),
    ("fetal_movement", 3, "I cant feel baby kicks"),
    ("fetal_movement", 4, "mtoto hachezi tumboni"),
    ("abdominal_pain", 0, "severe pain in my back"),
    ("abdominal_pain", 1, "I have stomach pain"),
    ("abdominal_pain", 2, "a sharp pain on my side"),
    ("abdominal_pain", 3, "tumbo kuuma sana"),
    ("water_breaking", 0, "I think my water breaks"),
    ("water_breaking", 1, "fluid gushing out"),
    ("water_breaking", 2, "I am leaking fluid"),
    ("water_breaking", 3, "maji yamekatika"),
    ("convulsions", 0, "she had a convulsion"),
    ("convulsions", 1, "I had a seizure"),
    ("convulsions", 2, "loss of consciousness"),
    ("convulsions", 3, "I keep fainting"),
    ("convulsions", 4, "I passed out yesterday"),
    ("convulsions", 5, "ana degedege"),
    ("convulsions", 6, "nilikuwa kupoteza fahamu"),
    ("swelling", 0, "severe swelling of my legs"),
    ("swelling", 1, "I have a swollen face"),
    ("swelling", 2, "miguu kuvimba sana"),
]

# One natural message per category in each language. Each Swahili message only
# matches through a Swahili pattern.
BILINGUAL_EXAMPLES: dict[str, dict[str, str]] = {
    "bleeding": {"en": "I am having heavy bleeding", "sw": "Ninatoka damu nyingi"},
    "headache_vision": {
        "en": "severe headache and my vision is blurred",
        "sw": "Nina kichwa kuuma na macho kuona vibaya",
    },
    "fever": {"en": "I have high fever", "sw": "Nina homa kali tangu jana"},
    "fetal_movement": {"en": "baby not moving since morning", "sw": "Mtoto hatembei tangu jana"},
    "abdominal_pain": {"en": "severe abdominal pain", "sw": "Tumbo kuuma sana"},
    "water_breaking": {"en": "my water broke", "sw": "Maji yamekatika asubuhi"},
    "convulsions": {"en": "she fainted and had a seizure", "sw": "Alipata degedege"},
    "swelling": {"en": "swollen hands and feet", "sw": "Uso wangu kuvimba sana"},
}

# Messages from backend/tests/unit/test_danger_signs.py plus edge cases.
EXISTING_TEST_MESSAGES: list[str] = [
    "I am having heavy bleeding",
    "There is excessive blood",
    "I see blood clots",
    "Ninatoka damu nyingi",
    "bleeding from down there",
    "I have a severe headache",
    "My vision is blurred",
    "I am seeing spots",
    "blurred vision since morning",
    "I have high fever",
    "severe fever and chills",
    "having chills all day",
    "nina homa kali",
    "reduced fetal movement",
    "no movement for hours",
    "baby not moving",
    "baby stopped moving",
    "I can't feel the baby",
    "baby isn't moving today",
    "severe abdominal pain",
    "sharp pain in my belly",
    "severe pain that won't stop",
    "stomach pain very bad",
    "my water broke",
    "water breaking right now",
    "fluid leaking from me",
    "leaking fluid down there",
    "I had a convulsion",
    "I had a seizure",
    "loss of consciousness",
    "I fainted today",
    "she passed out",
    "severe swelling in my face",
    "swollen hands and feet",
    "I have severe headache and heavy bleeding and I fainted",
]

NEGATIVE_MESSAGES: list[str] = [
    "What should I eat during pregnancy?",
    "When is my next appointment?",
    "How do I prepare for birth?",
    "My back aches a little",
    "I feel tired today",
    "Hello",
    "Thank you for the information",
    "Habari, nina swali kuhusu chakula",
    "Ninahitaji ushauri kuhusu kliniki",
    "",
    "20",
    "YES",
]

EDGE_CASE_MESSAGES: list[str] = [
    "HEAVY BLEEDING",
    "heavy\n\nbleeding",
    "Bleeding!!!",
    "MTOTO HATEMBEI",
    "my water   broke and I have chills",
    "nosebleeding",  # \b keeps this from matching
    "blur vision",  # not matched today: blurred? needs "blurre"
    "convulsions",  # not matched today: \bconvulsion\b
    "seizures",  # not matched today: \bseizure\b
    "baby stop moving",  # not matched today: stopped? needs "stoppe"
    "I pass out",  # not matched today: passed? needs "passe"
]
