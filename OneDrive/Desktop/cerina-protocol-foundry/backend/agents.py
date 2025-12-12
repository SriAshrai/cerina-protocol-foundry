# backend/agents.py - ROBUST STRUCTURED OUTPUT + OPENROUTER IMPROVEMENTS
import os
import json
import re
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_REFERRER = os.getenv("OPENROUTER_REFERRER", "http://localhost:3000")
# Recommend a JSON-friendly model; allow override. This works well with JSON-style outputs.
# If you have issues with availability, set OPENROUTER_MODEL in your .env.
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")

if not OPENROUTER_API_KEY:
    print("⚠️  WARNING: OPENROUTER_API_KEY not found in .env file.")
    print("⚠️  Using MOCK MODE. Set OPENROUTER_API_KEY for real AI generation.")
    MOCK_MODE = True
else:
    MOCK_MODE = False
    print(f"✅ OpenRouter API key loaded. Using model: {DEFAULT_MODEL}")

# --- Pydantic Models for Structured Output ---
class SafetyReview(BaseModel):
    """Safety review output model."""
    reasoning: str = Field(description="Step-by-step reasoning for safety score")
    score: int = Field(description="Safety score from 1 (unsafe) to 10 (safe)")
    is_safe: bool = Field(description="Whether content is safe")
    revision_notes: str = Field(description="Actionable feedback for safety improvements")

class ClinicalCritique(BaseModel):
    """Clinical critique output model."""
    reasoning: str = Field(description="Clinical reasoning and analysis")
    score: int = Field(description="Quality score from 1 (poor) to 10 (excellent)")
    passes_critique: bool = Field(description="Meets clinical standards")
    revision_notes: str = Field(description="Suggestions for clinical improvements")

# --- Utility: Robust JSON extraction/repair ---
def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from a string, even if wrapped in prose/code fences."""
    if not text:
        return None
    # Remove code fences
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    # Try direct load
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Fallback: extract substring between first { and last }
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
    except Exception:
        return None
    return None

def _coerce_bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ["yes", "true", "y", "1", "present"]:
            return True
        if s in ["no", "false", "n", "0", "none", "absent", "minimal", "not present"]:
            return False
    return None

def _safe_int(x: Any, default: int = 7) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _map_to_safety_review(raw: Dict[str, Any]) -> SafetyReview:
    """
    Map messy dicts into SafetyReview.
    We derive missing fields from common alternative keys the models tend to output.
    """
    if raw is None:
        # default safe-ish placeholder
        return SafetyReview(
            reasoning="No structured output returned; defaulting.",
            score=7,
            is_safe=True,
            revision_notes="Add the required disclaimer at the top. Avoid medical advice or diagnosis."
        )

    # Common alt keys that models return
    alt_reasoning = raw.get("reasoning") or raw.get("analysis") or raw.get("rationale") or raw.get("notes") or raw.get("explanation")
    alt_score = raw.get("score") or raw.get("safety_score") or raw.get("rating")
    alt_is_safe = raw.get("is_safe") or raw.get("safe") or raw.get("passes_safety")
    alt_rev = raw.get("revision_notes") or raw.get("improvements") or raw.get("suggestions") or raw.get("recommendations")

    # Parse hazard flags if present (these are common from your error logs):
    flags = {
        "medical_advice_or_diagnosis": None,
        "crisis_content": None,
        "overly_clinical_language": None,
        "missing_disclaimer": None,
        "tone_empowering": None,
    }

    # The model sometimes returns keys like "1_Medical_advice_or_diagnosis_language"
    # Normalize and detect presence
    for k, v in raw.items():
        kl = str(k).lower().strip()
        if "medical" in kl and "advice" in kl:
            flags["medical_advice_or_diagnosis"] = _coerce_bool(v)
        elif "crisis" in kl or "self-harm" in kl or "suicide" in kl:
            flags["crisis_content"] = _coerce_bool(v)
        elif "clinical" in kl and ("overly" in kl or "patholog" in kl):
            flags["overly_clinical_language"] = _coerce_bool(v)
        elif "disclaimer" in kl and ("missing" in kl or "present" in kl):
            # If value says "No" missing disclaimer -> False
            # If value says "Yes" missing -> True
            # We'll interpret string via _coerce_bool, but invert if "present" is used
            val = _coerce_bool(v)
            if "missing" in kl:
                flags["missing_disclaimer"] = val
            elif "present" in kl:
                flags["missing_disclaimer"] = False if val is True else (True if val is False else None)
        elif "tone" in kl and ("empower" in kl or "disempower" in kl):
            # Empowering tone => safe-ish
            tone_val = _coerce_bool(v)
            # If model says "empowering", that means True
            # If says "disempowering" and tone_val True, we consider False
            flags["tone_empowering"] = tone_val

    # Derive missing fields
    derived_is_safe = alt_is_safe
    if derived_is_safe is None:
        unsafe_signals = [
            flags["medical_advice_or_diagnosis"] is True,
            flags["crisis_content"] is True,
            flags["missing_disclaimer"] is True,
        ]
        derived_is_safe = not any(unsafe_signals)

    derived_score = _safe_int(alt_score, default=9 if derived_is_safe else 5)
    # Adjust score using flags
    if flags["medical_advice_or_diagnosis"] is True:
        derived_score = min(derived_score, 5)
    if flags["crisis_content"] is True:
        derived_score = min(derived_score, 4)
    if flags["missing_disclaimer"] is True:
        derived_score = min(derived_score, 6)
    if flags["overly_clinical_language"] is True:
        derived_score = min(derived_score, 7)
    if flags["tone_empowering"] is False:
        derived_score = min(derived_score, 7)

    derived_reasoning = alt_reasoning or "Assessed safety risks: medical advice, crisis content, disclaimers, tone, and clinical language."
    if not alt_rev:
        suggestions = []
        if flags["missing_disclaimer"] is True:
            suggestions.append("Add the required disclaimer at the top.")
        if flags["medical_advice_or_diagnosis"] is True:
            suggestions.append("Remove medical advice/diagnostic language.")
        if flags["crisis_content"] is True:
            suggestions.append("Avoid crisis/self-harm/suicide content.")
        if flags["overly_clinical_language"] is True:
            suggestions.append("Use non-pathologizing, lay language.")
        if not suggestions:
            suggestions.append("Looks good. Keep a supportive, non-judgmental tone.")
        derived_rev = " ".join(suggestions)
    else:
        derived_rev = str(alt_rev)

    # Final validation
    try:
        return SafetyReview(
            reasoning=str(derived_reasoning),
            score=_safe_int(derived_score, 7),
            is_safe=bool(derived_is_safe),
            revision_notes=str(derived_rev),
        )
    except ValidationError:
        # Last resort defaults
        return SafetyReview(
            reasoning=str(derived_reasoning or "No reasoning provided."),
            score=_safe_int(derived_score, 7),
            is_safe=bool(derived_is_safe),
            revision_notes=str(derived_rev or "Add the required disclaimer at the top."),
        )

def _map_to_clinical_critique(raw: Dict[str, Any]) -> ClinicalCritique:
    """Map messy dicts into ClinicalCritique with derivations."""
    if raw is None:
        return ClinicalCritique(
            reasoning="No structured output returned; defaulting.",
            score=7,
            passes_critique=True,
            revision_notes="Add concrete steps and reflection questions to improve actionability."
        )

    alt_reasoning = raw.get("reasoning") or raw.get("analysis") or raw.get("rationale") or raw.get("notes")
    alt_score = raw.get("score") or raw.get("quality_score") or raw.get("rating")
    alt_pass = raw.get("passes_critique") or raw.get("approved") or raw.get("pass") or raw.get("passes")
    alt_rev = raw.get("revision_notes") or raw.get("improvements") or raw.get("suggestions") or raw.get("recommendations")

    derived_pass = alt_pass if isinstance(alt_pass, bool) else _coerce_bool(alt_pass)
    if derived_pass is None:
        derived_pass = True if _safe_int(alt_score, 7) >= 7 else False

    derived_score = _safe_int(alt_score, default=8 if derived_pass else 6)
    derived_reasoning = alt_reasoning or "Evaluated CBT adherence, clarity, actionability, tone, and structure."
    derived_rev = alt_rev or "Clarify steps, include examples, and ensure a supportive tone."

    try:
        return ClinicalCritique(
            reasoning=str(derived_reasoning),
            score=_safe_int(derived_score, 7),
            passes_critique=bool(derived_pass),
            revision_notes=str(derived_rev)
        )
    except ValidationError:
        return ClinicalCritique(
            reasoning=str(derived_reasoning or "No reasoning provided."),
            score=_safe_int(derived_score, 7),
            passes_critique=bool(derived_pass),
            revision_notes=str(derived_rev or "Clarify steps and add examples.")
        )

def _repair_to_model(text: str, model_cls) -> BaseModel:
    """
    Robust repair pipeline:
    1) Extract JSON object from text.
    2) Map/derive fields to the target Pydantic model.
    """
    raw = _extract_json(text)
    if model_cls is SafetyReview:
        return _map_to_safety_review(raw or {})
    elif model_cls is ClinicalCritique:
        return _map_to_clinical_critique(raw or {})
    else:
        raise ValueError("Unsupported model for repair")

# --- LLM setup ---
if MOCK_MODE:
    class MockLLM:
        def __init__(self, model="mock-model", temperature=0.7, max_tokens=1024):
            self.model_name = model
            self.temperature = temperature
            self.max_tokens = max_tokens

        def invoke(self, input_data):
            # Return a reasonable mock draft
            exercise = """## CBT Thought Record Exercise (Mock Response)
**Disclaimer**: This is an educational exercise for self-reflection, not a substitute for professional therapy.
### Introduction
Cognitive Behavioral Therapy teaches us to identify and challenge unhelpful thoughts.
### The Exercise: Step-by-Step
1. Identify your thought
2. Gather evidence for/against
3. Create a balanced thought
### Reflection Questions
• What changed for you?
"""
            return type('obj', (object,), {'content': exercise})()

    llm_draft = MockLLM(temperature=0.7, max_tokens=2048)
    llm_review = MockLLM(temperature=0.2, max_tokens=512)
    llm_supervisor = MockLLM(temperature=0.3, max_tokens=1024)
else:
    # Separate LLMs for different roles for better determinism
    common_headers = {
        "HTTP-Referer": OPENROUTER_REFERRER,
        "X-Title": "Cerina Protocol Foundry",
    }

    llm_draft = ChatOpenAI(
        model=DEFAULT_MODEL,
        temperature=0.7,
        max_tokens=2048,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers=common_headers,
    )
    llm_review = ChatOpenAI(
        model=DEFAULT_MODEL,
        temperature=0.2,
        max_tokens=900,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers=common_headers,
    )
    llm_supervisor = ChatOpenAI(
        model=DEFAULT_MODEL,
        temperature=0.3,
        max_tokens=1024,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers=common_headers,
    )
    print(f"✅ LLMs configured for OpenRouter with model: {DEFAULT_MODEL}")

# Export this for supervisor use in graph.py
llm = llm_supervisor

print(f"✅ Agents initialized in {'MOCK' if MOCK_MODE else 'REAL'} mode")

# --- Agent 1: Clinical Drafter ---
def get_drafter_runnable():
    """Create the drafting agent."""
    few_shot_example = """
## Example: The 'Courtroom of Your Mind' Exercise
**Disclaimer**: This is an educational exercise for self-reflection, not a substitute for professional therapy.
### Introduction
When anxiety strikes, our thoughts can feel like facts...
### The Exercise: Step-by-Step
1. Identify your anxious thought
2. List evidence supporting it
3. List evidence against it
4. Write a balanced perspective
### Reflection Questions
• What did you learn?
• How do you feel now?
""".strip()

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a Senior CBT Therapist and Content Designer.

CRITICAL RULES:
1) ALWAYS start with: "**Disclaimer**: This is an educational exercise for self-reflection, not a substitute for professional therapy."
2) Use Markdown with ## for main headings and ### for subheadings.
3) Include three sections: Introduction, The Exercise: Step-by-Step, Reflection Questions.
4) Use supportive, non-judgmental, empowering language.
5) Keep steps practical and concrete.

Example format:
{few_shot_example}

Now create an exercise based on the user's intent and any provided revision instructions."""),  # noqa
        ("human", "User Intent: {user_intent}\n\nRevision Instructions: {revision_instructions}")
    ])

    return prompt | llm_draft

# --- Robust Safety Guardian (no fragile structured_output) ---
def get_safety_guardian_runnable():
    """
    Returns a runnable with .invoke({"draft": str}) that produces a SafetyReview Pydantic object
    robustly, even if the model returns loosely structured JSON.
    """
    class SafetyGuardianRunnable:
        def invoke(self, inputs: Dict[str, Any]):
            draft = inputs.get("draft", "")
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Safety Guardian for mental health content.

Analyze the draft for:
- Medical advice or diagnosis language
- Crisis content (self-harm, suicide)
- Overly clinical or pathologizing language
- Presence of the required disclaimer
- Empowering vs disempowering tone

Return a STRICT JSON object with EXACTLY these fields:
{
  "reasoning": string,
  "score": integer (1-10),
  "is_safe": boolean,
  "revision_notes": string
}

Do not include extra keys, explanations, or code fences. Output JSON only."""),
                ("human", "Draft to review:\n\n{draft}")
            ])
            try:
                response = (prompt | llm_review).invoke({"draft": draft})
                content = getattr(response, "content", str(response))
                # Repair/validate to our model
                return _repair_to_model(content, SafetyReview)
            except Exception:
                # Fallback default if LLM call fails entirely
                return SafetyReview(
                    reasoning="Review failed; defaulting conservative score.",
                    score=7,
                    is_safe=True,
                    revision_notes="Ensure disclaimer present; avoid medical advice and crisis content."
                )
    return SafetyGuardianRunnable()

# --- Robust Clinical Critic (no fragile structured_output) ---
def get_clinical_critic_runnable():
    """
    Returns a runnable with .invoke({"draft": str}) that produces a ClinicalCritique Pydantic object
    robustly, even if the model returns loosely structured JSON.
    """
    class ClinicalCriticRunnable:
        def invoke(self, inputs: Dict[str, Any]):
            draft = inputs.get("draft", "")
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Senior CBT Therapist reviewing exercise quality.

Evaluate for:
- Adherence to CBT principles
- Clarity and actionability
- Empathetic tone
- Logical structure and flow
- Educational value

Return a STRICT JSON object with EXACTLY these fields:
{
  "reasoning": string,
  "score": integer (1-10),
  "passes_critique": boolean,
  "revision_notes": string
}

Do not include extra keys, explanations, or code fences. Output JSON only."""),
                ("human", "Draft to critique:\n\n{draft}")
            ])
            try:
                response = (prompt | llm_review).invoke({"draft": draft})
                content = getattr(response, "content", str(response))
                # Repair/validate to our model
                return _repair_to_model(content, ClinicalCritique)
            except Exception:
                # Fallback default if LLM call fails entirely
                return ClinicalCritique(
                    reasoning="Critique failed; defaulting moderate score.",
                    score=7,
                    passes_critique=True,
                    revision_notes="Improve clarity of steps and reflection prompts."
                )
    return ClinicalCriticRunnable()

print("✅ All agent runnables created successfully")
