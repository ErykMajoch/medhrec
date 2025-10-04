from datetime import datetime, timedelta, timezone
from typing import Callable


def generate_wrapped_func(function: Callable, cache: dict) -> Callable:
    def wrapper(*args, **kwargs):
        now = datetime.now(timezone.utc)
        cache_key = (args, tuple(sorted(kwargs.items())))
        if cache_key in cache:
            if now >= cache[cache_key].get("expiry"):
                result = function(*args, **kwargs)
                expiry = now + timedelta(seconds=86400)
                cache[cache_key] = {"result": result, "expiry": expiry}

            return cache[cache_key].get("result")
        else:
            result = function(*args, **kwargs)
            expiry = now + timedelta(seconds=86400)
            cache[cache_key] = {"result": result, "expiry": expiry}
            return result

    return wrapper


def commander_cache(func):
    cmdr_cache = {}
    wrapper_func = generate_wrapped_func(func, cmdr_cache)
    return wrapper_func


def card_detail_cache(func):
    detail_cache = {}
    wrapper_func = generate_wrapped_func(func, detail_cache)
    return wrapper_func


def combo_cache(func):
    combo_cache = {}
    wrapper_func = generate_wrapped_func(func, combo_cache)
    return wrapper_func


def average_deck_cache(func):
    avg_deck_cache = {}
    wrapper_func = generate_wrapped_func(func, avg_deck_cache)
    return wrapper_func


def deck_cache(func):
    deck_cache = {}
    wrapper_func = generate_wrapped_func(func, deck_cache)
    return wrapper_func
