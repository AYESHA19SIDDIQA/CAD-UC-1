"""
LLM integration service - supports multiple LLM providers
"""
import json
import time
from typing import Any, Dict, List, Optional
from openai import OpenAI
import google.generativeai as genai
from app.config import get_settings

class LLMService:
    """Service for interacting with LLM APIs"""
    
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
        }
        return profiles

    def _resolve_profile(self, model_profile: str) -> Dict[str, str]:
        """Resolve profile name to provider/model pair."""
        profiles = self.get_model_profiles()
        if model_profile not in profiles:
            available = ", ".join(profiles.keys())
            raise ValueError(f"Unknown model_profile '{model_profile}'. Available: {available}")
        return profiles[model_profile]
    
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
            return self._extract_with_openai(prompt, model_override=model)
                
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
        
        # Try to parse JSON from response
        # Sometimes LLM wraps JSON in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse JSON response
        data = json.loads(content)
        return data
    
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
        
        # Try to parse JSON from response
        # Sometimes LLM wraps JSON in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse JSON response
        data = json.loads(content)
        return data
    
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
            return self._generate_with_openai(prompt, max_tokens, temperature, model_override=model)
                
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

    def benchmark_profiles(
        self,
        prompt: str,
        profiles: Optional[List[str]] = None,
        runs: int = 1,
        mode: str = "extract"
    ) -> List[Dict[str, Any]]:
        """Run repeatable side-by-side performance comparison across model profiles."""
        selected_profiles = profiles or ["existing", "deepseek_small", "qwen_small"]
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
                except Exception as exc:  # Defensive fallback if internal handlers change
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
