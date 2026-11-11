"""Tokenisation and stemming for Russian and Kazakh legal text.

Modes:
  word  lower-cased word forms
  p5    first five characters of a word (a standard crude stemmer for agglutinative languages)
  stem  Russian: Snowball; Kazakh: iterative suffix stripping (see KK_SUFFIXES)
Stemming is cached per distinct word form, so a corpus of hundreds of millions of tokens costs only
as many stemmer calls as there are different word forms.
"""
import re
from functools import lru_cache

TOKEN = re.compile(r"[^\W_]+")
CYR = re.compile(r"[а-яёәғқңөұүһі]")
LAT = re.compile(r"[a-z]")
# Latin letters that stand in for Cyrillic ones inside otherwise Cyrillic words (a data defect, e.g. "пpомышленности")
LOOKALIKE = str.maketrans({"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у", "k": "к", "m": "м", "h": "н", "t": "т", "b": "в", "i": "і"})

RU_STOP = set("""и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее мне было вот от меня еще нет о из ему
теперь когда даже ну ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя ничего ей может они тут где есть надо
ней для мы тебя их чем была сам чтоб без будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой совсем ним здесь этом
один почти мой тем чтобы нее сейчас были куда зачем всех никогда можно при наконец два об другой хоть после над больше тот через эти нас про
всего них какая много разве три эту моя впрочем свою этой перед иногда лучше чуть том нельзя такой им более всегда конечно всю между
какие какое какую каких какими кого кому кем ком чему чем""".split())
KK_STOP = set("""және мен бен пен да де та те деген бұл осы сол ол үшін туралы бойынша немесе болып болады ретінде арқылы не ал бір
қандай қалай қайда қашан неше нені кім кімнің нені бола ма ме па пе ба бе""".split())
STOP = {"ru": RU_STOP, "kk": KK_STOP}

KK_SUFFIXES = sorted(
    ["лар", "лер", "дар", "дер", "тар", "тер", "ның", "нің", "дың", "дің", "тың", "тің", "дан", "ден", "тан", "тен", "нан", "нен",
     "мен", "бен", "пен", "да", "де", "та", "те", "на", "не", "ға", "ге", "қа", "ке", "ны", "ні", "ды", "ді", "ты", "ті", "ын", "ін",
     "ының", "інің", "ында", "інде", "ынан", "інен", "ымен", "імен", "сы", "сі", "ы", "і"],
    key=len, reverse=True)
MIN_STEM = 3

_snowball = None


def _ru_snowball(word):
    global _snowball
    if _snowball is None:
        from nltk.stem.snowball import SnowballStemmer
        _snowball = SnowballStemmer("russian")
    return _snowball.stem(word)


def _kk_strip(word):
    for _ in range(3):
        for suf in KK_SUFFIXES:
            if word.endswith(suf) and len(word) - len(suf) >= MIN_STEM:
                word = word[: -len(suf)]
                break
        else:
            break
    return word


@lru_cache(maxsize=None)
def stem_word(lang, mode, word):
    if mode == "word":
        return word
    if mode == "p5":
        return word[:5]
    return _ru_snowball(word) if lang == "ru" else _kk_strip(word)


def normalise_token(tok):
    if LAT.search(tok) and CYR.search(tok):
        tok = tok.translate(LOOKALIKE)
    return tok


def char_ngrams(tok, lo=3, hi=5):
    padded = f"#{tok}#"
    return [padded[i:i + n] for n in range(lo, hi + 1) for i in range(len(padded) - n + 1)]


def analyze(text, lang="ru", mode="stem"):
    stop = STOP[lang]
    out = []
    for tok in TOKEN.findall(text.lower().replace("ё", "е")):
        tok = normalise_token(tok)
        if tok in stop or (len(tok) < 2 and not tok.isdigit()):
            continue
        if mode == "char":
            out.extend(char_ngrams(tok))
        else:
            out.append(stem_word(lang, mode, tok))
    return out
