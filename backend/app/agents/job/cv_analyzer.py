from typing import Optional

from shared.ai import analyze_cv_with_fallback


def analyze_job_cv(
    text: str,
    target_lang: str = "français",
    selected_model: str = "Groq / Llama 3.3",
    gemini_api_key: str = "",
    xai_api_key: str = "",
    groq_api_key: str = "",
    ollama_url: str = "http://localhost:11434",
    custom_gemini_key: Optional[str] = None,
    force_fallback_mode: bool = False,
) -> dict:
    """Delegate to the existing shared CV analysis for job seekers."""
    return analyze_cv_with_fallback(
        text=text,
        target_lang=target_lang,
        selected_model=selected_model,
        gemini_api_key=gemini_api_key,
        xai_api_key=xai_api_key,
        groq_api_key=groq_api_key,
        ollama_url=ollama_url,
        custom_gemini_key=custom_gemini_key,
        force_fallback_mode=force_fallback_mode,
    )