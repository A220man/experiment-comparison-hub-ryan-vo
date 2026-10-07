import json
import logging
from typing import Any, Dict, Optional
import httpx
from backend.app.core.config import settings
from backend.app.models.schemas import AdvisoryExplanationResponse

logger = logging.getLogger('experiment_hub.llm')
ADVISORY_DISCLAIMER = "Advisory only. Model interpretations are automatically grounded in calculated Pareto frontiers and Welch's t-test hypothesis statistics. Evaluate independently before production deployment."

def build_evidence_context(evidence_summary: Dict[str, Any]) -> str:
    lines = [
        'EMPIRICAL EXPERIMENT RECORDS AND STATISTICAL EVIDENCE:',
        f"Experiment: {evidence_summary.get('experiment_name', 'N/A')}",
        f"Baseline Variant: {evidence_summary.get('baseline_variant', 'N/A')}",
        '',
        'PARETO FRONTIER EVIDENCE:',
        f"- Total Runs Evaluated: {evidence_summary.get('total_runs', 0)}",
        f"- Frontier Optimal Count: {evidence_summary.get('frontier_count', 0)}",
        f"- Knee Point Compromise: {evidence_summary.get('knee_point', 'None')}",
        f"- Hypervolume Coverage Indicator: {evidence_summary.get('hypervolume', 0.0)}",
        '',
        "STATISTICAL SIGNIFICANCE EVIDENCE (Welch's t-test, alpha=0.05):",
    ]
    for comp in evidence_summary.get('comparisons', []):
        lines.append(f"- {comp.get('treatment_variant')} vs {comp.get('baseline_variant')} on {comp.get('metric')}: Mean Delta={comp.get('mean_delta')}, Welch p={comp.get('p_value_welch')}, Cohen's d={comp.get('cohens_d')}, Result={comp.get('significance_label')}")
    lines.append('\nTASK: Synthesize a concise, technically rigorous trade-off advisory grounded strictly in the data above.')
    return '\n'.join(lines)

def generate_deterministic_offline_summary(evidence_summary: Dict[str, Any], experiment_id: str) -> AdvisoryExplanationResponse:
    knee = evidence_summary.get('knee_point') or 'Not designated'
    hv = evidence_summary.get('hypervolume', 0.0)
    comps = evidence_summary.get('comparisons', [])
    significant_gains = [c for c in comps if c.get('is_statistically_significant') and 'Improvement' in c.get('significance_label', '')]
    significant_drops = [c for c in comps if c.get('is_statistically_significant') and 'Degradation' in c.get('significance_label', '')]
    inconclusive = [c for c in comps if not c.get('is_statistically_significant')]
    body_lines = [
        '### Deterministic Empirical Advisory Summary',
        f"**Pareto Optimization Profile**: Evaluated {evidence_summary.get('total_runs', 0)} runs with {evidence_summary.get('frontier_count', 0)} non-dominated configurations on the frontier (Hypervolume indicator: {hv:.4f}).",
        f"**Recommended Knee Point**: `{knee}` was determined as the optimal compromise minimizing normalized distance to the ideal utopia vector.",
        '',
        '**Multi-Seed Hypothesis Test Findings**:',
    ]
    if significant_gains:
        body_lines.append(f"- **Statistically Verified Gains ({len(significant_gains)})**:")
        for g in significant_gains:
            body_lines.append(f"  * `{g.get('treatment_variant')}` over baseline on `{g.get('metric')}`: Delta: {g.get('mean_delta'):+.4f} ({g.get('percent_change'):+.2f}%), Welch p={g.get('p_value_welch'):.4f}, Cohen's d={g.get('cohens_d'):.2f}.")
    else:
        body_lines.append('- **No statistically significant improvements detected** across treatment variants.')
    if significant_drops:
        body_lines.append(f"- **Statistically Verified Degradations ({len(significant_drops)})**:")
        for d in significant_drops:
            body_lines.append(f"  * `{d.get('treatment_variant')}` regressed on `{d.get('metric')}`: Delta: {d.get('mean_delta'):+.4f}, Welch p={d.get('p_value_welch'):.4f}.")
    if inconclusive:
        body_lines.append(f"- **Inconclusive / Random Seed Noise ({len(inconclusive)})**:")
        for inc in inconclusive:
            body_lines.append(f"  * `{inc.get('treatment_variant')}` on `{inc.get('metric')}` (p={inc.get('p_value_welch'):.4f} >= 0.05). Variance is consistent with random seed fluctuations.")
    body_text = '\n'.join(body_lines)
    return AdvisoryExplanationResponse(experiment_id=experiment_id, provider='offline-deterministic', model='rule-based-statistical-engine', is_advisory=True, disclaimer=ADVISORY_DISCLAIMER, offline_fallback=True, advisory_text=body_text, evidence_summary=evidence_summary)

async def generate_advisory_explanation(evidence_summary: Dict[str, Any], experiment_id: str) -> AdvisoryExplanationResponse:
    if not settings.llm_api_key and settings.llm_provider.lower() != 'ollama':
        return generate_deterministic_offline_summary(evidence_summary, experiment_id)
    evidence_text = build_evidence_context(evidence_summary)
    prompt = 'Please explain the Pareto frontier trade-offs, identify the knee point compromise, and interpret the hypothesis test results.'
    try:
        p = settings.llm_provider.lower()
        base = settings.llm_base_url.rstrip('/')
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            if p == 'anthropic':
                resp = await client.post(f'{base}/v1/messages', json={'model': settings.llm_model, 'messages': [{'role': 'user', 'content': f'{evidence_text}\n\n{prompt}'}], 'system': 'You are an AI/ML research assistant.', 'max_tokens': 1024, 'temperature': 0.2}, headers={'x-api-key': settings.llm_api_key or '', 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'})
                resp.raise_for_status()
                text = resp.json()['content'][0]['text']
            elif p == 'gemini':
                resp = await client.post(f'{base}/v1beta/models/{settings.llm_model}:generateContent', params={'key': settings.llm_api_key}, json={'contents': [{'parts': [{'text': f'{evidence_text}\n\n{prompt}'}]}], 'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 1024}})
                resp.raise_for_status()
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
            elif p == 'ollama':
                resp = await client.post(f'{base}/api/chat', json={'model': settings.llm_model, 'messages': [{'role': 'user', 'content': f'{evidence_text}\n\n{prompt}'}], 'stream': False})
                resp.raise_for_status()
                text = resp.json()['message']['content']
            else:
                resp = await client.post(f'{base}/chat/completions', json={'model': settings.llm_model, 'messages': [{'role': 'system', 'content': 'You are an AI/ML research assistant.'}, {'role': 'user', 'content': f'{evidence_text}\n\n{prompt}'}], 'temperature': 0.2, 'max_tokens': 1024}, headers={'Authorization': f'Bearer {settings.llm_api_key}', 'Content-Type': 'application/json'})
                resp.raise_for_status()
                text = resp.json()['choices'][0]['message']['content']
        return AdvisoryExplanationResponse(experiment_id=experiment_id, provider=settings.llm_provider, model=settings.llm_model, is_advisory=True, disclaimer=ADVISORY_DISCLAIMER, offline_fallback=False, advisory_text=text, evidence_summary=evidence_summary)
    except Exception as exc:
        error_msg = str(exc)
        if settings.llm_api_key and settings.llm_api_key in error_msg:
            error_msg = error_msg.replace(settings.llm_api_key, '[REDACTED_SECRET]')
        logger.warning(f'LLM provider error ({settings.llm_provider}): {error_msg}. Using deterministic fallback.')
        offline_resp = generate_deterministic_offline_summary(evidence_summary, experiment_id)
        offline_resp.disclaimer = f'{ADVISORY_DISCLAIMER} (Upstream provider error: {error_msg[:120]})'
        return offline_resp
