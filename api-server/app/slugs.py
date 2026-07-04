import random
import string

_ADJECTIVES = [
    "brave", "calm", "clever", "crimson", "eager", "fuzzy", "gentle", "golden",
    "happy", "icy", "jolly", "keen", "lively", "misty", "nimble", "orange",
    "proud", "quiet", "rapid", "sandy", "silent", "swift", "tiny", "vivid",
    "witty", "zesty",
]

_NOUNS = [
    "badger", "canyon", "comet", "delta", "ember", "falcon", "glacier",
    "harbor", "island", "jaguar", "kestrel", "lagoon", "meadow", "nebula",
    "otter", "pebble", "quartz", "raven", "summit", "tundra", "urchin",
    "valley", "willow", "yonder", "zephyr",
]


def generate_slug() -> str:
    """Generate a subdomain like 'brave-otter-4f2a', matching what the
    original Node version got for free from `random-word-slugs`."""
    adjective = random.choice(_ADJECTIVES)
    noun = random.choice(_NOUNS)
    suffix = "".join(random.choices(string.hexdigits.lower()[:16], k=4))
    return f"{adjective}-{noun}-{suffix}"
