import json
import re
from typing import Optional, Any
import requests

from .caching import (
    commander_cache,
    card_detail_cache,
    combo_cache,
    average_deck_cache,
    deck_cache,
)

from .utils import get_random_ua, available_brackets, available_tags, available_budgets


class EDHRec:
    def __init__(self, cookies: str = None):
        self.cookies = cookies
        self.session = requests.Session()
        if self.cookies:
            self.session.cookies = self.get_cookie_jar(cookies)
        self.session.headers = {
            "Accept": "application/json",
            "User-Agent": get_random_ua(),
        }
        self.base_url = "https://edhrec.com"
        self._json_base_url = "https://json.edhrec.com/cards"
        self._api_base_url = f"{self.base_url}/api"
        self.default_build_id = "mI7k8IZ23x74LocK_h-qe"
        self.current_build_id = None

        self.available_brackets = available_brackets
        self.available_tags = available_tags
        self.available_budgets = available_budgets

        self._commander_data_cache = {}

    @staticmethod
    def get_cookie_jar(cookie_str: str):
        if cookie_str.startswith("userState="):
            cookie_str = cookie_str.split("userState=")[1]

        d = {"userState": cookie_str}
        cookie_jar = requests.cookies.cookiejar_from_dict(d)
        return cookie_jar

    @staticmethod
    def format_card_name(card_name: str) -> str:
        # card names are all lower case
        card_name = card_name.lower()
        # Spaces need to be converted to underscores
        card_name = card_name.replace(" ", "-")
        # remove apostrophes
        card_name = card_name.replace("'", "")
        # remove commas
        card_name = card_name.replace(",", "")
        return card_name

    @staticmethod
    def _format_list(items: list) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return f"'{items[0]}'"
        if len(items) == 2:
            return f"'{items[0]}' and '{items[1]}'"
        return ", ".join(f"'{item}'" for item in items[:-1]) + f" and '{items[-1]}'"

    @staticmethod
    def _get_nextjs_data(response: dict) -> Optional[dict]:
        if "pageProps" in response:
            return response.get("pageProps", {}).get("data")
        return None

    def _get(
        self,
        uri: str,
        query_params: dict = None,
        return_type: str = "json",
        config_context: dict = None,
    ) -> bytes | None | Any:
        res = self.session.get(uri, params=query_params)

        if res.status_code == 404:
            # Build informative error message if context is provided
            if config_context:
                config_parts = []
                if config_context.get("card_name"):
                    config_parts.append(f"commander '{config_context['card_name']}'")
                if config_context.get("bracket"):
                    config_parts.append(f"bracket '{config_context['bracket']}'")
                if config_context.get("tag"):
                    config_parts.append(f"tag '{config_context['tag']}'")
                if config_context.get("budget"):
                    config_parts.append(f"budget '{config_context['budget']}'")

                config_str = ", ".join(config_parts)
                data_type = config_context.get("data_type", "data")
                raise Exception(
                    f"No {data_type} available on EDHRec for this configuration: {config_str}. "
                    f"This combination may not have enough data on the website."
                )
            else:
                # Generic 404 error if no context provided
                raise Exception(f"Resource not found: {uri}")

        res.raise_for_status()
        if return_type == "json":
            res_json = res.json()
            return res_json
        else:
            return res.content

    def get_build_id(self) -> Optional[str]:
        home_page = self._get(self.base_url, return_type="raw")
        home_page_content = home_page.decode("utf-8")
        script_block_regex = (
            r"<script id=\"__NEXT_DATA__\" type=\"application/json\">(.*)</script>"
        )
        if script_match := re.findall(script_block_regex, home_page_content):
            props_str = script_match[0]
        else:
            return None
        try:
            props_data = json.loads(props_str)
            return props_data.get("buildId")
        except json.JSONDecodeError:
            return None

    def check_build_id(self):
        if not self.current_build_id:
            self.current_build_id = self.get_build_id()
            # If we couldn't get the current buildId we'll try to fall back to a known static string
            if not self.current_build_id:
                self.current_build_id = self.default_build_id
        # We have a build ID set
        return True

    def _build_nextjs_uri(
        self,
        endpoint: str,
        card_name: str,
        bracket: str = None,
        tag: str = None,
        budget: str = None,
    ):
        self.check_build_id()
        formatted_card_name = self.format_card_name(card_name)
        query_params = {"commanderName": formatted_card_name}
        uri = f"{self.base_url}/_next/data/{self.current_build_id}/{endpoint}/{formatted_card_name}"

        if bracket:
            if bracket in self.available_brackets:
                uri += f"/{bracket}"
            else:
                raise Exception(
                    f"Invalid bracket parameter passed: '{budget}'. Only {self._format_list(self.available_brackets)} available."
                )

        if tag:
            if tag in self.available_tags:
                uri += f"/{tag}"
                if not budget:
                    query_params["themeName"] = tag
            else:
                raise Exception(
                    f"Invalid tag parameter passed: '{tag}'. Only {self._format_list(self.available_tags)} available."
                )

        if budget:
            if budget in self.available_budgets:
                uri += f"/{budget}"
                query_params["themeName"] = budget
            else:
                raise Exception(
                    f"Invalid budget parameter passed: '{budget}'. Only {self._format_list(self.available_budgets)} available."
                )
        uri += f".json"

        if endpoint == "combos":
            query_params["colors"] = formatted_card_name

        return uri, query_params

    def _get_cardlist_from_container(
        self,
        card_name: str,
        category: str = None,
        bracket: str = None,
        tag: str = None,
        budget: str = None,
    ) -> dict:
        card_data = self.get_commander_data(
            card_name, bracket=bracket, tag=tag, budget=budget
        )
        container = card_data.get("container", {})
        json_dict = container.get("json_dict", {})
        card_lists = json_dict.get("cardlists")
        result = {}
        for cl in card_lists:
            _card_list = cl.get("cardviews")
            _header = cl.get("header")
            _tag = cl.get("tag")
            if category:
                if _tag == category:
                    result[_header] = _card_list
                    return result
            else:
                result[_header] = _card_list
        return result

    def get_card_list(self, card_list: list) -> dict:
        uri = f"{self._api_base_url}/cards"
        req_body = {"format": "dict", "names": card_list}
        res = self.session.post(uri, json=req_body)
        res.raise_for_status()
        res_json = res.json()
        return res_json

    def get_card_link(self, card_name: str) -> str:
        formatted_card_name = self.format_card_name(card_name)
        uri = f"{self.base_url}/cards/{formatted_card_name}"
        return uri

    @card_detail_cache
    def get_card_details(self, card_name: str) -> dict:
        formatted_card_name = self.format_card_name(card_name)
        uri = f"{self._json_base_url}/{formatted_card_name}"
        res = self._get(uri)
        return res

    @combo_cache
    def get_card_combos(self, card_name: str) -> dict:
        combo_uri, params = self._build_nextjs_uri("combos", card_name)
        res = self._get(combo_uri, query_params=params)
        data = self._get_nextjs_data(res)
        return data

    def get_combo_url(self, combo_url: str) -> str:
        uri = f"{self.base_url}"
        if combo_url.startswith("/"):
            uri += combo_url
        else:
            uri += f"/{combo_url}"
        return uri

    @commander_cache
    def get_commander_data(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        commander_uri, params = self._build_nextjs_uri(
            "commanders", card_name, bracket=bracket, tag=tag, budget=budget
        )

        config_context = {
            "card_name": card_name,
            "bracket": bracket,
            "tag": tag,
            "budget": budget,
            "data_type": "data",
        }

        res = self._get(
            commander_uri, query_params=params, config_context=config_context
        )
        data = self._get_nextjs_data(res)
        return data

    @average_deck_cache
    def get_commanders_average_deck(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        average_deck_uri, params = self._build_nextjs_uri(
            "average-decks", card_name, bracket=bracket, tag=tag, budget=budget
        )

        config_context = {
            "card_name": card_name,
            "bracket": bracket,
            "tag": tag,
            "budget": budget,
            "data_type": "average deck data",
        }

        res = self._get(
            average_deck_uri, query_params=params, config_context=config_context
        )
        data = self._get_nextjs_data(res)
        deck_obj = {"commander": card_name, "decklist": data.get("deck")}
        return deck_obj

    @deck_cache
    def get_commander_decks(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        average_deck_uri, params = self._build_nextjs_uri(
            "decks", card_name, bracket=bracket, tag=tag, budget=budget
        )

        config_context = {
            "card_name": card_name,
            "bracket": bracket,
            "tag": tag,
            "budget": budget,
            "data_type": "deck data",
        }

        res = self._get(
            average_deck_uri, query_params=params, config_context=config_context
        )
        data = self._get_nextjs_data(res)
        return data

    def get_commander_type_distributions(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        commander_data = self.get_commander_data(
            card_name, bracket=bracket, tag=tag, budget=budget
        )
        data = {}
        for segment in commander_data["panels"]["piechart"]["content"]:
            data[segment["label"]] = segment["value"]
        return data

    def get_commander_tags(self, card_name: str, bracket: str = None) -> dict:
        commander_data = self.get_commander_data(card_name, bracket=bracket)
        data = {}
        for tag in commander_data["panels"]["taglinks"]:
            data[tag["value"]] = tag["count"]
        return data

    def get_commander_mana_curve(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        commander_data = self.get_commander_data(
            card_name, bracket=bracket, tag=tag, budget=budget
        )
        return commander_data["panels"]["mana_curve"]

    def get_commander_cards(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_new_cards(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "newcards", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_high_synergy_cards(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "highsynergycards", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_cards(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "topcards", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_creatures(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "creatures", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_instants(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "instants", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_sorceries(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "sorceries", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_artifacts(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "utilityartifacts", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_mana_artifacts(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "manaartifacts", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_enchantments(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "enchantments", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_battles(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "battles", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_planeswalkers(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "planeswalkers", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_lands(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "lands", bracket=bracket, tag=tag, budget=budget
        )
        return card_list

    def get_top_utility_lands(
        self, card_name: str, bracket: str = None, tag: str = None, budget: str = None
    ) -> dict:
        card_list = self._get_cardlist_from_container(
            card_name, "utilitylands", bracket=bracket, tag=tag, budget=budget
        )
        return card_list
