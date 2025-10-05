# mEDHRec

## Overview
This is a fork of [PyEDHRec](https://github.com/stainedhat/pyedhrec) which is a python wrapper around the [EDHREC](https://edhrec.com/) website with some added features I found to be missing form the original. Currently, EDHREC does not provide an API 
so the intent of this library is to enable people to build automated tooling around the useful information EDHREC provides.

## Installation
This project will not be on PyPI, so here are the steps to use the library locally:
1. Clone the repository
```bash
git clone https://github.com/ErykMajoch/medhrec
```

2. Install library requirements
```bash
python -m pip install -r requirements.txt
```
3. Use the library locally!


## Usage
Create an instance of the edhrec client

```python
from medhrec import EDHRec

edhrec = EDHRec()

# Reference cards by the exact card name, the library will format as needed
helga = "Helga, Skittish Seer"

# Specify optional query parameters to filter results
# All available brackets, tags and budgets can be found in medhrec/utils.py
bracket = "upgraded"
tag = "midrange"
budget = "budget"

# Get basic card details
details = edhrec.get_card_details(helga)

# Get details for a list of cards
card_list = edhrec.get_card_list(["Pongify", "Farseek"])

# Get an edhrec.com link for a given card
helga_link = edhrec.get_card_link(helga)

# Get combos for a card
helga_combos = edhrec.get_card_combos(helga)

# Get commander tags
helga_tags = edhrec.get_commander_tags(helga, bracket=bracket)

# Get commander data (supports bracket, tag, and budget parameters)
helga_commander_data = edhrec.get_commander_data(helga, bracket=bracket, tag=tag, budget=budget)

# Get cards commonly associated with a commander
helga_cards = edhrec.get_commander_cards(helga, bracket=bracket, tag=tag, budget=budget)

# Get the average decklist for a commander
helga_avg_deck = edhrec.get_commanders_average_deck(helga, bracket=bracket, tag=tag, budget=budget)

# Get known deck lists for a commander
helga_decks = edhrec.get_commander_decks(helga, bracket=bracket, tag=tag, budget=budget)

# Get average commander deck type distribution
helga_type_distribution = edhrec.get_commander_type_distributions(helga, bracket=bracket, tag=tag, budget=budget)

# Get average commander deck mana curve
helga_mc = edhrec.get_commander_mana_curve(helga, bracket=bracket, tag=tag, budget=budget)

# This library provides several methods to get specific types of recommended cards
# All of these methods support bracket, tag, and budget parameters
new_cards = edhrec.get_new_cards(helga, bracket=bracket, tag=tag, budget=budget)
high_synergy_cards = edhrec.get_high_synergy_cards(helga, bracket=bracket, tag=tag, budget=budget)

# Get all top cards
top_cards = edhrec.get_top_cards(helga, bracket=bracket, tag=tag, budget=budget)

# Get specific top cards by type
top_creatures = edhrec.get_top_creatures(helga, bracket=bracket, tag=tag, budget=budget)
top_instants = edhrec.get_top_instants(helga, bracket=bracket, tag=tag, budget=budget)
top_sorceries = edhrec.get_top_sorceries(helga, bracket=bracket, tag=tag, budget=budget)
top_enchantments = edhrec.get_top_enchantments(helga, bracket=bracket, tag=tag, budget=budget)
top_artifacts = edhrec.get_top_artifacts(helga, bracket=bracket, tag=tag, budget=budget)
top_mana_artifacts = edhrec.get_top_mana_artifacts(helga, bracket=bracket, tag=tag, budget=budget)
top_battles = edhrec.get_top_battles(helga, bracket=bracket, tag=tag, budget=budget)
top_planeswalkers = edhrec.get_top_planeswalkers(helga, bracket=bracket, tag=tag, budget=budget)
top_utility_lands = edhrec.get_top_utility_lands(helga, bracket=bracket, tag=tag, budget=budget)
top_lands = edhrec.get_top_lands(helga, bracket=bracket, tag=tag, budget=budget)

```

## Query Parameters
Most commander-related methods support the following optional parameters to filter results:
- **bracket**: Filter by power level (exhibition, core, upgraded, optimized, cedh)
- **tag**: Filter by deck theme/archetype (e.g., midrange, aggro, combo)
- **budget**: Filter by budget constraint ("budget" or "expensive")

For a complete list of available tags and other options, see `medhrec/utils.py`.

**Note**: Not all combinations of parameters may have data available on EDHRec. If a configuration doesn't exist, the library will raise an exception with a message about the missing data.

## Caching
To avoid excessive requests to edhrec.com this library uses in-memory caching for card retrieval methods. Each time you run 
a script using this library we'll cache the results for any given card. If you request the card again during the same execution we 
will use the cached value until the cache expires (defaults to 24 hours). If you use a long running script know that card data will only 
be updated once a day. Due to the nature of the game not changing often this should normally not cause issues and will help alleviate 
excessive traffic to EDHREC servers.