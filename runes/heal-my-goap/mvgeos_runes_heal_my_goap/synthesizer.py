"""LLM bridge action synthesizer interfacing with OpenRouter API."""

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from mvgeos_runes_heal_my_goap.models import (
    Action,
    Gap,
    SynthesizedAction,
    SynthesizedActionSchema,
)

load_dotenv()


class BaseSynthesizer(ABC):
    """Abstract interface for GOAP action synthesizers."""

    @abstractmethod
    def synthesize_bridge_action(
        self,
        gap: Gap,
        available_actions: list[Action],
        failed_attempts: list[Action] | None = None,
    ) -> Action:
        """Synthesizes a bridge action to resolve missing precondition gaps.

        Args:
            gap: Diagnostic Gap object containing missing predicates.
            available_actions: Currently known GOAP actions.
            failed_attempts: Optional list of actions that previously failed.

        Returns:
            A synthesized Action instance.
        """


class LLMSynthesizer(BaseSynthesizer):
    """Action synthesizer using OpenRouter LLM structured outputs.

    Attributes:
        api_key: OpenRouter API key string.
        model: OpenRouter target model identifier string.
        base_url: Base URL string for OpenRouter API requests.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        """Initializes LLMSynthesizer.

        Args:
            api_key: Optional OpenRouter API key string.
            model: Optional OpenRouter target model string.
            base_url: Base URL for OpenRouter API endpoints.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv(
            "DEFAULT_LLM_MODEL", "nvidia/nemotron-3-550b-a55b:free"
        )
        self.base_url = base_url

    def _generate_wildcard_action(self, gap: Gap) -> Action:
        """Generates fallback deterministic wildcard bridge action.

        Args:
            gap: Diagnostic Gap object.

        Returns:
            A fallback Action matching missing predicates.
        """
        pred_repr = (
            list(gap.missing_predicate.keys())[0]
            if gap.missing_predicate
            else "unknown"
        )
        short_id = gap.id[:8]
        return SynthesizedAction(
            name=f"synth_wildcard_{pred_repr}_{short_id}",
            preconditions={},
            effects=gap.missing_predicate.copy(),
            cost=50,
            description=f"Fallback wildcard action satisfying {pred_repr}.",
        )

    def synthesize_bridge_action(
        self,
        gap: Gap,
        available_actions: list[Action],
        failed_attempts: list[Action] | None = None,
    ) -> Action:
        """Synthesizes a bridge action via LLM synthesis or wildcard fallback.

        Args:
            gap: Missing precondition gap details.
            available_actions: List of existing available actions.
            failed_attempts: Optional list of previously failed actions.

        Returns:
            A synthesized Action object resolving missing gap.
        """
        if not self.api_key:
            return self._generate_wildcard_action(gap)

        attempts_list = failed_attempts or []
        missing_str = json.dumps(gap.missing_predicate)
        failed_names = [a.name for a in attempts_list]
        failed_str = ", ".join(failed_names) if failed_names else "None"

        system_prompt = (
            "You are a Senior AI Planning Engineer creating a single GOAP "
            "Action. Respond ONLY with a valid JSON object matching this "
            'schema:\n{\n  "name": "action_name_snake_case",\n  '
            '"description": "Short description",\n  "preconditions": '
            '{"state_key": boolean_or_value},\n  "effects": '
            '{"missing_state_key": missing_state_value},\n  "cost": 10.0,'
            '\n  "is_idempotent": true,\n  "code_payload": null\n}\n'
            f"CRITICAL REQUIREMENT: The action effects MUST satisfy: "
            f"{missing_str}.\nThe action cost MUST be >= 10.0.\n"
            f"Do NOT generate any of the following failed actions: "
            f"{failed_str}."
        )

        user_prompt = (
            f"Isolate Missing Gap: {missing_str}\n"
            f"Dependent Action: "
            f"{gap.dependent_action_name or 'Goal Requirement'}\n"
            f"Closest State: {json.dumps(gap.closest_state)}\n"
            "Synthesize a single valid GOAP Action JSON object."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"
        max_retries = 3

        for attempt in range(max_retries):
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }

            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code in (429, 502, 503, 504):
                        time.sleep(2**attempt)
                        continue
                    if resp.status_code != 200:
                        break

                    data = resp.json()
                    content = str(data["choices"][0]["message"]["content"])
                    action_data = json.loads(content)

                    if "effects" in action_data and isinstance(
                        action_data["effects"], dict
                    ):
                        action_data["effects"].update(gap.missing_predicate)

                    schema_inst = SynthesizedActionSchema(**action_data)

                    raw_name = schema_inst.name.replace("synth_", "")
                    short_hash = hashlib.sha256(
                        content.encode("utf-8")
                    ).hexdigest()[:6]
                    namespaced_name = f"synth_{raw_name}_{short_hash}"

                    return SynthesizedAction(
                        name=namespaced_name,
                        preconditions=schema_inst.preconditions,
                        effects=schema_inst.effects,
                        cost=int(schema_inst.cost),
                        description=schema_inst.description,
                        code=schema_inst.code_payload,
                    )
            except (
                ValidationError,
                json.JSONDecodeError,
                KeyError,
                httpx.HTTPError,
            ) as err:
                user_prompt += (
                    f"\nPrevious attempt failed with error: {err!s}. "
                    "Please correct JSON format."
                )
                time.sleep(0.5)

        return self._generate_wildcard_action(gap)
