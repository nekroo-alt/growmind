import os
import json
import re
from v1.core.telemetry import telemetry


class LLMProvider:
    """
    Simple wrapper for LLM calls to abstract prompts from logic.
    Supports OpenAI and Anthropic, with a mock fallback for MVP development.
    """

    def __init__(self, provider=None, model=None, providers=None):
        if providers:
            self.providers = providers
        else:
            p = provider or os.getenv("LLM_PROVIDER", "google").lower()
            m = model or self._get_default_model(p)
            self.providers = [{"provider": p, "model": m}]

        self.current_index = 0
        self._update_active_provider()

    def _update_active_provider(self):
        """Sets the current provider state based on current_index."""
        config = self.providers[self.current_index]
        self.provider = config["provider"]
        self.model = config["model"]
        self.api_key = self._get_api_key(self.provider)

    def _get_default_model(self, provider=None):
        p = provider or self.provider
        if p == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4o")
        elif p == "anthropic":
            return os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
        elif p == "google":
            return os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
        return "mock-model"

    def _get_api_key(self, provider=None):
        p = provider or self.provider
        if p == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif p == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif p == "google":
            return os.getenv("GOOGLE_API_KEY")
        return None

    def count_tokens(self, text):
        """
        Estimate the number of tokens in a string.
        Uses tiktoken if available, otherwise falls back to a heuristic.
        """
        if not text:
            return 0
        try:
            import tiktoken

            try:
                encoding = tiktoken.encoding_for_model(self.model)
            except (KeyError, AttributeError):
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # Fallback heuristic: ~4 characters per token
            return (len(text) + 3) // 4

    def calculate_cost(self, prompt_tokens, completion_tokens):
        """
        Estimate the cost of an LLM call based on the provider and model.
        Returns estimated cost in USD.
        """
        # Prices per 1M tokens (Approximate pricing as of late 2024)
        pricing = {
            "gpt-4o": {"prompt": 5.0, "completion": 15.0},
            "claude-3-5-sonnet-20240620": {"prompt": 3.0, "completion": 15.0},
            "claude-3-opus-20240229": {"prompt": 15.0, "completion": 75.0},
            "claude-3-haiku-20240307": {"prompt": 0.25, "completion": 1.25},
            "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
            "gemini-1.5-pro": {"prompt": 3.50, "completion": 10.50},
        }

        # Handle potential version differences in model strings
        model_key = self.model
        if "gpt-4o" in model_key:
            model_key = "gpt-4o"

        model_pricing = pricing.get(model_key)
        if not model_pricing:
            # Try matching prefixes if exact match fails
            for key, rates in pricing.items():
                if key in self.model:
                    model_pricing = rates
                    break

        if not model_pricing:
            return 0.0

        prompt_cost = (prompt_tokens / 1_000_000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * model_pricing["completion"]

        return round(prompt_cost + completion_cost, 6)

    def call(self, system_prompt, user_prompt, temperature=0.7, max_tokens=1000):
        """
        Executes an LLM call with retry/failover logic across multiple providers.
        Returns a dictionary with 'content', 'usage', and 'cost'.
        """
        max_attempts = len(self.providers)
        last_error = ""

        for _ in range(max_attempts):
            self._update_active_provider()

            if not self.api_key:
                last_error = f"Error: Missing API key for {self.provider}"
                if self.provider == "mock":
                    content = self._mock_call(system_prompt, user_prompt)
                    prompt_tokens = self.count_tokens(system_prompt + user_prompt)
                    completion_tokens = self.count_tokens(content)
                    telemetry.log_llm_interaction(
                        self.provider, self.model, system_prompt, user_prompt, content
                    )
                    return {
                        "content": content,
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens,
                        },
                        "cost": 0.0,
                    }

                # Try next provider
                self.current_index = (self.current_index + 1) % max_attempts
                continue

            try:
                if self.provider == "openai":
                    content, p_tokens, c_tokens = self._call_openai(
                        system_prompt, user_prompt, temperature, max_tokens
                    )
                elif self.provider == "anthropic":
                    content, p_tokens, c_tokens = self._call_anthropic(
                        system_prompt, user_prompt, temperature, max_tokens
                    )
                elif self.provider == "google":
                    content, p_tokens, c_tokens = self._call_google(
                        system_prompt, user_prompt, temperature, max_tokens
                    )
                else:
                    raise ValueError(f"Unsupported provider '{self.provider}'")

                cost = self.calculate_cost(p_tokens, c_tokens)
                telemetry.log_llm_usage(p_tokens + c_tokens, cost)
                telemetry.log_llm_interaction(
                    self.provider, self.model, system_prompt, user_prompt, content
                )
                return {
                    "content": content,
                    "usage": {
                        "prompt_tokens": p_tokens,
                        "completion_tokens": c_tokens,
                        "total_tokens": p_tokens + c_tokens,
                    },
                    "cost": cost,
                }
            except Exception as e:
                last_error = f"Error calling {self.provider}: {str(e)}"
                # Switch to next provider for next attempt
                self.current_index = (self.current_index + 1) % max_attempts

        error_content = f"Error: All LLM providers failed. Last error: {last_error}"
        telemetry.log_llm_interaction(
            "None", "None", system_prompt, user_prompt, error_content
        )
        return {
            "content": error_content,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "cost": 0.0,
        }

    def _call_openai(self, system_prompt, user_prompt, temperature, max_tokens):
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            usage = response.usage
            return content, usage.prompt_tokens, usage.completion_tokens
        except ImportError:
            raise ImportError("'openai' library not installed.")
        except Exception as e:
            raise e

    def _call_anthropic(self, system_prompt, user_prompt, temperature, max_tokens):
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = response.content[0].text
            usage = response.usage
            return content, usage.input_tokens, usage.output_tokens
        except ImportError:
            raise ImportError("'anthropic' library not installed.")
        except Exception as e:
            raise e

    def _call_google(self, system_prompt, user_prompt, temperature, max_tokens):
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                model_name=self.model, system_instruction=system_prompt
            )
            response = model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature, max_output_tokens=max_tokens
                ),
            )
            content = response.text
            # Gemini's usage_metadata might not always be available or structured the same
            try:
                p_tokens = response.usage_metadata.prompt_token_count
                c_tokens = response.usage_metadata.candidates_token_count
            except AttributeError:
                p_tokens = self.count_tokens(system_prompt + user_prompt)
                c_tokens = self.count_tokens(content)

            return content, p_tokens, c_tokens
        except ImportError:
            raise ImportError("'google-generativeai' library not installed.")
        except Exception as e:
            raise e

    def _mock_call(self, system_prompt, user_prompt):
        """
        Fallback mock response for testing when no API key is provided.
        Returns a format that's often expected by the planner/implementor.
        """
        if "Break down the given requirements" in system_prompt:
            # Return a JSON list if it looks like a planning request
            return json.dumps(
                [
                    {
                        "title": "Mock Task 1",
                        "acceptance_criteria": "Criteria 1",
                        "module": "mock",
                    },
                    {
                        "title": "Mock Task 2",
                        "acceptance_criteria": "Criteria 2",
                        "module": "mock",
                    },
                ]
            )

        return f"Mock response for {self.model}. No API key provided."

    def call_multi_file(
        self, system_prompt, user_prompt, temperature=0.7, max_tokens=2000
    ):
        """
        Calls the LLM and parses the response into a dictionary of {filepath: content}.
        Returns a dictionary with 'files', 'usage', and 'cost'.
        """
        result = self.call(system_prompt, user_prompt, temperature, max_tokens)
        files = self.parse_multi_file_response(result["content"])
        return {
            "files": files,
            "usage": result["usage"],
            "cost": result["cost"],
            "raw_content": result["content"],
        }

    def parse_multi_file_response(self, response):
        """
        Parses a string containing multiple file blocks into a dictionary.
        Expected format in response:
        File: path/to/file.py
        ```python
        content
        ```
        """
        files = {}
        # Pattern to match file path followed by code block
        pattern = r"(?:File: |### )?([a-zA-Z0-9_\-\./]+)[\r\n]+```[a-zA-Z-]*[\r\n]+([\s\S]*?)[\r\n]+```"

        matches = re.finditer(pattern, response)
        for match in matches:
            path = match.group(1).strip()
            # Only accept as path if it contains a dot or a slash
            if "." in path or "/" in path:
                content = match.group(2)
                files[path] = content

        return files
