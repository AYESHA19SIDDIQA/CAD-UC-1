"""
LLM integration service - supports multiple LLM providers including local models (Qwen, DeepSeek)
"""
import json
import time
from typing import Any, Dict, List, Optional, Union
from openai import OpenAI
import google.generativeai as genai
from app.config import get_settings

# For local models
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not installed. Local models will not be available.")

class LLMService:
    """Service for interacting with LLM APIs and local models"""

    # Class-level cache for loaded local models
    _loaded_models: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.provider = settings.llm_provider
        self.client: Optional[OpenAI] = None
        self.gemini_client = None

        if self.provider == "gemini":
            # Configure Gemini
            if not settings.validate_gemini_key():
                raise ValueError(
                    "Gemini API key not configured. "
                    "Please set GEMINI_API_KEY in .env file"
                )
            genai.configure(api_key=settings.gemini_api_key)
            self.model = settings.gemini_model
            self.temperature = settings.gemini_temperature
            self.max_tokens = settings.gemini_max_tokens
            self.gemini_client = genai.GenerativeModel(self.model)

        elif self.provider in ["openai", "openrouter"]:
            # Configure OpenAI/OpenRouter defaults
            self.model = settings.openai_model
            self.temperature = settings.openai_temperature
            self.max_tokens = settings.openai_max_tokens
            self._ensure_openai_client()

        elif self.provider == "local":
            # For local models, no initial client; we'll load on demand
            self.model = settings.local_model_name  # e.g., "Qwen/Qwen2.5-1.5B-Instruct"
            self.temperature = settings.local_temperature
            self.max_tokens = settings.local_max_tokens
            if not TRANSFORMERS_AVAILABLE:
                raise ImportError("transformers library is required for local models")

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _ensure_openai_client(self) -> OpenAI:
        """Create OpenAI-compatible client lazily to support mixed-provider benchmarking."""
        if self.client is not None:
            return self.client

        if not self.settings.validate_openai_key():
            raise ValueError(
                "API key not configured. "
                "Please set OPENAI_API_KEY in .env file"
            )

        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url
        )
        return self.client

    def get_model_profiles(self) -> Dict[str, Dict[str, str]]:
        """Return available model profiles that can be selected per call."""
        profiles: Dict[str, Dict[str, str]] = {
            "existing": {
                "provider": self.provider,
                "model": self.model,
            },
            "deepseek_small": {
                "provider": "openai_compatible",
                "model": self.settings.deepseek_small_model,
            },
            "qwen_small": {
                "provider": "openai_compatible",
                "model": self.settings.qwen_small_model,
            },
            # NEW: local profiles for CPU inference
            "qwen_small_local": {
                "provider": "local",
                "model": "Qwen/Qwen2.5-1.5B-Instruct",  # you can override via settings
            },
            "deepseek_small_local": {
                "provider": "local",
                "model": "deepseek-ai/deepseek-coder-1.3b-instruct",
            },
        }
        return profiles

    def _resolve_profile(self, model_profile: str) -> Dict[str, str]:
        """Resolve profile name to provider/model pair."""
        profiles = self.get_model_profiles()
        if model_profile not in profiles:
            available = ", ".join(profiles.keys())
            raise ValueError(f"Unknown model_profile '{model_profile}'. Available: {available}")
        return profiles[model_profile]

    # ========== Local model loading and inference ==========
    def _load_local_model(self, model_name: str) -> Dict[str, Any]:
        """Load a Hugging Face model and tokenizer, cache it, and return the model objects."""
        if model_name in self._loaded_models:
            return self._loaded_models[model_name]

        print(f"Loading local model {model_name} for the first time (this may take a while)...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,  # Use float32 for CPU
                device_map="auto",
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            model.eval()
        except Exception as e:
            raise RuntimeError(f"Failed to load local model {model_name}: {e}")

        # Cache
        self._loaded_models[model_name] = {
            "model": model,
            "tokenizer": tokenizer,
        }
        print(f"Model {model_name} loaded successfully.")
        return self._loaded_models[model_name]

    def _generate_with_local(
        self,
        prompt: str,
        model_name: str,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text using a local Hugging Face model."""
        cached = self._load_local_model(model_name)
        model = cached["model"]
        tokenizer = cached["tokenizer"]

        # Format prompt with chat template if needed
        messages = [{"role": "user", "content": prompt}]
        try:
            # Attempt to apply chat template
            formatted_prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            # Fallback: just use raw prompt
            formatted_prompt = prompt

        inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)

        # Move inputs to CPU (already on CPU)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Remove the input prompt from the output
        input_ids_length = inputs['input_ids'].shape[1]
        generated_tokens = outputs[0][input_ids_length:]
        response = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        return response
        
    def _extract_with_local(self, prompt: str, model_name: str) -> Dict:
        """Extract structured data using a local model."""
        raw_output = self._generate_with_local(prompt, model_name)
        return self._parse_json_from_output(raw_output)

    # ========== Common JSON parsing ==========
    def _parse_json_from_output(self, content: str) -> Dict:
        """Extract JSON from LLM output, handling markdown code blocks."""
        # Try to parse JSON from response
        # Sometimes LLM wraps JSON in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Parse JSON response
        data = json.loads(content)
        return data

    # ========== Public extraction methods ==========
    def extract_structured_data(self, prompt: str, model_profile: str = "existing") -> Dict:
        """
        Extract structured data using LLM

        Args:
            prompt: Prompt for the LLM
            model_profile: Which configured model profile to use

        Returns:
            Extracted data as dictionary
        """
        try:
            profile = self._resolve_profile(model_profile)
            provider = profile["provider"]
            model = profile["model"]

            if provider == "gemini":
                return self._extract_with_gemini(prompt)
            elif provider == "openai_compatible":
                return self._extract_with_openai(prompt, model_override=model)
            elif provider == "local":
                return self._extract_with_local(prompt, model)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        except Exception as e:
            print(f"LLM extraction error ({model_profile}): {e}")
            return {}

    def _extract_with_gemini(self, prompt: str) -> Dict:
        """Extract data using Gemini API"""
        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }

        full_prompt = f"""You are a helpful assistant that extracts structured data from documents. Always respond with valid JSON.

{prompt}"""

        response = self.gemini_client.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        content = response.text
        return self._parse_json_from_output(content)

    def _extract_with_openai(self, prompt: str, model_override: Optional[str] = None) -> Dict:
        """Extract data using OpenAI API"""
        client = self._ensure_openai_client()
        response = client.chat.completions.create(
            model=model_override or self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from documents. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        content = response.choices[0].message.content
        return self._parse_json_from_output(content)

    # ========== Text generation ==========
    def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model_profile: str = "existing"
    ) -> str:
        """
        Generate text using LLM

        Args:
            prompt: Prompt for text generation
            max_tokens: Maximum tokens to generate (uses config default if None)
            temperature: Temperature for generation (uses config default if None)
            model_profile: Which configured model profile to use

        Returns:
            Generated text
        """
        try:
            profile = self._resolve_profile(model_profile)
            provider = profile["provider"]
            model = profile["model"]

            if provider == "gemini":
                return self._generate_with_gemini(prompt, max_tokens, temperature)
            elif provider == "openai_compatible":
                return self._generate_with_openai(prompt, max_tokens, temperature, model_override=model)
            elif provider == "local":
                return self._generate_with_local(prompt, model, max_new_tokens=max_tokens, temperature=temperature)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        except Exception as e:
            print(f"Text generation error ({model_profile}): {e}")
            return ""

    def _generate_with_gemini(self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """Generate text using Gemini API"""
        generation_config = {
            "temperature": temperature or self.temperature,
            "max_output_tokens": max_tokens or self.max_tokens,
        }

        response = self.gemini_client.generate_content(
            prompt,
            generation_config=generation_config
        )

        return response.text

    def _generate_with_openai(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """Generate text using OpenAI API"""
        client = self._ensure_openai_client()
        response = client.chat.completions.create(
            model=model_override or self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature
        )

        return response.choices[0].message.content

    # ========== Benchmarking ==========
    def benchmark_profiles(
        self,
        prompt: str,
        profiles: Optional[List[str]] = None,
        runs: int = 1,
        mode: str = "extract"
    ) -> List[Dict[str, Any]]:
        """Run repeatable side-by-side performance comparison across model profiles."""
        selected_profiles = profiles or ["existing", "deepseek_small", "qwen_small", "qwen_small_local", "deepseek_small_local"]
        results: List[Dict[str, Any]] = []

        for profile_name in selected_profiles:
            profile = self._resolve_profile(profile_name)
            latencies: List[float] = []
            success_count = 0
            last_error = None

            for _ in range(max(1, runs)):
                start = time.perf_counter()
                try:
                    if mode == "extract":
                        payload = self.extract_structured_data(prompt, model_profile=profile_name)
                        ok = bool(payload)
                    else:
                        text = self.generate_text(prompt, model_profile=profile_name)
                        ok = bool(text and text.strip())
                    if ok:
                        success_count += 1
                except Exception as exc:
                    last_error = str(exc)
                finally:
                    latencies.append(time.perf_counter() - start)

            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            results.append(
                {
                    "profile": profile_name,
                    "provider": profile["provider"],
                    "model": profile["model"],
                    "runs": len(latencies),
                    "success_rate": success_count / len(latencies) if latencies else 0.0,
                    "avg_latency_seconds": round(avg_latency, 3),
                    "min_latency_seconds": round(min(latencies), 3) if latencies else 0.0,
                    "max_latency_seconds": round(max(latencies), 3) if latencies else 0.0,
                    "last_error": last_error,
                }
            )

        return results
