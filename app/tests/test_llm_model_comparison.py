"""
Compare LLM model profiles (existing, deepseek small, qwen small)
for document-structuring style prompts.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_input_text(input_file: str) -> str:
    """Load plain text content for benchmarking."""
    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def build_prompt(raw_text: str) -> str:
    """Create a stable extraction prompt for cross-model comparison."""
    return f"""
You are a banking sanctions document extraction assistant.

Extract these fields from the text and return valid JSON only:
- customer_name
- approval_number
- approval_date
- business_segment
- facilities (array of objects with facility_type, facility_amount, tenor, profit_rate)
- terms_conditions (array of top 5 key terms)

If a field is missing, use null.

Document text:
{raw_text}
"""


def print_summary(results):
    """Print concise benchmark summary to console."""
    print("\n" + "=" * 110)
    print("LLM MODEL COMPARISON SUMMARY")
    print("=" * 110)
    print(
        f"{'Profile':<18}{'Provider':<20}{'Model':<40}{'Success':<12}{'Avg Latency(s)':<16}"
    )
    print("-" * 110)

    for item in results:
        success_pct = f"{item['success_rate'] * 100:.0f}% ({item['runs']})"
        print(
            f"{item['profile']:<18}"
            f"{item['provider']:<20}"
            f"{item['model']:<40}"
            f"{success_pct:<12}"
            f"{item['avg_latency_seconds']:<16}"
        )

    print("=" * 110)


def main():
    """Run side-by-side model benchmark."""
    parser = argparse.ArgumentParser(description="Compare existing, DeepSeek small and Qwen small profiles")
    parser.add_argument(
        "--input",
        default=r"app\extracted_text\Sanction Advice Word Global Technologies Services_converted_extracted_20260307_002000.txt",
        help="Input text file path for prompt context",
    )
    parser.add_argument("--runs", type=int, default=None, help="Number of runs per profile")
    args = parser.parse_args()

    from config import get_settings
    from services.llm_service import LLMService

    settings = get_settings()
    runs = max(1, args.runs or settings.model_benchmark_runs)

    print("=" * 80)
    print("LLM PROFILE BENCHMARK")
    print("=" * 80)
    print(f"Input file: {args.input}")
    print(f"Runs per profile: {runs}")
    print(f"Current provider/model: {settings.llm_provider} / {settings.gemini_model if settings.llm_provider == 'gemini' else settings.openai_model}")

    raw_text = load_input_text(args.input)
    prompt = build_prompt(raw_text)

    llm_service = LLMService()
    profiles = ["existing", "deepseek_small", "qwen_small"]
    results = llm_service.benchmark_profiles(prompt=prompt, profiles=profiles, runs=runs, mode="extract")

    print_summary(results)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"llm_profile_benchmark_{timestamp}.json"
    output_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\nSaved benchmark report: {output_file}")


if __name__ == "__main__":
    main()
