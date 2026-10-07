import logging
from typing import Any, Dict
import httpx
from backend.app.core.config import settings
from backend.app.models.schemas import AdvisoryExplanationResponse

logger = logging.getLogger('experiment_hub.llm')
ADVISORY_DISCLAIMER = "Advisory only. Model interpretations are automatically grounded in calculated Pareto frontiers and Welch's t-test hypothesis statistics. Evaluate independently before production deployment."

def build_evidence_context(ev: Dict[str, Any]) -> str:
    lines = [f"Experiment: {ev.get('experiment_name', 'N/A')}, Baseline: {ev.get('baseline_variant', 'N/A')}", f"Runs: {ev.get('total_runs', 0)}, Frontier: {ev.get('frontier_count', 0)}, Knee: {ev.get('knee_point', 'None')}, Hypervolume: {ev.get('hypervolume', 0.0)}"]
    for c in ev.get('comparisons', []):
        lines.append(f"{c.get('treatment_variant')} vs {c.get('baseline_variant')} ({c.get('metric')}): delta={c.get('mean_delta')}, p={c.get('p_value_welch')}, d={c.get('cohens_d')}, res={c.get('significance_label')}")
    return '\n'.join(lines)

def generate_deterministic_offline_summary(ev: Dict[str, Any], experiment_id: str) -> AdvisoryExplanationResponse:
    knee = ev.get('knee_point') or 'None'
    comps = ev.get('comparisons', [])
    gains = [c for c in comps if c.get('is_statistically_significant') and 'Improvement' in c.get('significance_label', '')]
    drops = [c for c in comps if c.get('is_statistically_significant') and 'Degradation' in c.get('significance_label', '')]
    b = [
        '### Deterministic Empirical Advisory Summary',
        f"**Pareto Profile**: {ev.get('total_runs', 0)} runs evaluated, {ev.get('frontier_count', 0)} frontier points. Knee: `{knee}` (HV: {ev.get('hypervolume', 0.0):.4f}).",
        '**Hypothesis Tests**:',
    ]
    if gains:
        b.extend(f"- Gain: `{g.get('treatment_variant')}` on `{g.get('metric')}` (delta {g.get('mean_delta'):+.4f}, p={g.get('p_value_welch'):.4f}, d={g.get('cohens_d'):.2f})" for g in gains)
    else:
        b.append('- No statistically significant improvements detected.')
    if drops:
        b.extend(f"- Degradation: `{d.get('treatment_variant')}` on `{d.get('metric')}` (delta {d.get('mean_delta'):+.4f}, p={d.get('p_value_welch'):.4f})" for d in drops)
    return AdvisoryExplanationResponse(experiment_id=experiment_id, provider='offline-deterministic', model='rule-based-statistical-engine', is_advisory=True, disclaimer=ADVISORY_DISCLAIMER, offline_fallback=True, advisory_text='\n'.join(b), evidence_summary=ev)

async def generate_advisory_explanation(ev: Dict[str, Any], experiment_id: str) -> AdvisoryExplanationResponse:
    if not settings.llm_api_key and settings.llm_provider.lower() != 'ollama':
        return generate_deterministic_offline_summary(ev, experiment_id)
    txt, q = build_evidence_context(ev), 'Explain trade-offs and hypothesis results.'
    try:
        p, base = settings.llm_provider.lower(), settings.llm_base_url.rstrip('/')
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            if p == 'anthropic':
                r = await client.post(f'{base}/v1/messages', json={'model': settings.llm_model, 'messages': [{'role': 'user', 'content': f'{txt}\n\n{q}'}], 'system': 'AI assistant', 'max_tokens': 1024}, headers={'x-api-key': settings.llm_api_key or '', 'anthropic-version': '2023-06-01'})
                r.raise_for_status(); text = r.json()['content'][0]['text']
            elif p == 'gemini':
                r = await client.post(f'{base}/v1beta/models/{settings.llm_model}:generateContent', params={'key': settings.llm_api_key}, json={'contents': [{'parts': [{'text': f'{txt}\n\n{q}'}]}]})
                r.raise_for_status(); text = r.json()['candidates'][0]['content']['parts'][0]['text']
            elif p == 'ollama':
                r = await client.post(f'{base}/api/chat', json={'model': settings.llm_model, 'messages': [{'role': 'user', 'content': f'{txt}\n\n{q}'}], 'stream': False})
                r.raise_for_status(); text = r.json()['message']['content']
            else:
                r = await client.post(f'{base}/chat/completions', json={'model': settings.llm_model, 'messages': [{'role': 'user', 'content': f'{txt}\n\n{q}'}]}, headers={'Authorization': f'Bearer {settings.llm_api_key}'})
                r.raise_for_status(); text = r.json()['choices'][0]['message']['content']
        return AdvisoryExplanationResponse(experiment_id=experiment_id, provider=settings.llm_provider, model=settings.llm_model, is_advisory=True, disclaimer=ADVISORY_DISCLAIMER, offline_fallback=False, advisory_text=text, evidence_summary=ev)
    except Exception as exc:
        msg = str(exc)
        if settings.llm_api_key and settings.llm_api_key in msg: msg = msg.replace(settings.llm_api_key, '[REDACTED_SECRET]')
        logger.warning(f'LLM error: {msg}')
        res = generate_deterministic_offline_summary(ev, experiment_id)
        res.disclaimer = f'{ADVISORY_DISCLAIMER} (Upstream provider error: {msg[:120]})'
        return res
