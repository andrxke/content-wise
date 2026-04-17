import numpy as np
from tribev2.utils import get_hcp_roi_indices, get_topk_rois

# Brain regions relevant to "focus" vs "being lured in"
FOCUS_REGIONS = {
    # ── Deep Focus / Executive Control ──
    "prefrontal": {
        "rois": ["p9-46v", "a9-46v", "46", "9-46d", "8BM", "8Av", "8Ad"],
        "function": "Executive control, sustained attention, working memory",
        "indicates": "FOCUSED — student is actively processing/reasoning"
    },
    "dlpfc": {
        "rois": ["9-46d", "46", "p9-46v"],
        "function": "Dorsolateral prefrontal cortex — goal-directed behavior",
        "indicates": "FOCUSED — deliberate, effortful thinking"
    },
    "ips_attention": {
        "rois": ["AIP", "LIPv", "LIPd", "MIP", "VIP"],
        "function": "Intraparietal sulcus — top-down attention control",
        "indicates": "FOCUSED — actively directing attention to content"
    },
    "language_processing": {
        "rois": ["55b", "STV", "TPOJ1", "PSL", "SFL", "PEF"],
        "function": "Language comprehension network",
        "indicates": "FOCUSED — processing textual/verbal content"
    },

    # ── Being Lured / Reward-Driven Engagement ──
    "visual_salience": {
        "rois": ["V1", "V2", "V3", "V4", "MT", "MST", "V3A", "V3B"],
        "function": "Primary + motion visual processing",
        "indicates": "VISUAL_ENGAGEMENT — strong visual stimulation"
    },
    "ventral_attention": {
        "rois": ["FOP1", "FOP2", "FOP3", "FOP4", "FOP5"],
        "function": "Ventral attention / salience network",
        "indicates": "LURED — stimulus-driven (bottom-up) attention capture"
    },
    "default_mode": {
        "rois": ["POS1", "POS2", "RSC", "v23ab", "d23ab", "31pv", "7m",
                 "PCV", "10r", "10v", "25", "s32", "a24"],
        "function": "Default mode network — mind wandering, self-referential",
        "indicates": "DISTRACTED — mind wandering, not engaged with content"
    },
    "reward_emotional": {
        "rois": ["OFC", "pOFC", "10r", "10v", "25", "a24", "p24"],
        "function": "Orbitofrontal / emotional processing",
        "indicates": "LURED — emotionally engaging but not educationally productive"
    },
    "auditory_engagement": {
        "rois": ["A1", "A4", "A5", "RI", "TA2", "MBelt", "LBelt", "PBelt"],
        "function": "Auditory cortex",
        "indicates": "AUDIO_ENGAGED — processing sound/music/speech"
    }
}

def interpret_brain_activity(mean_pred: np.ndarray) -> dict:
    """
    Interpret TribeV2's predicted brain activity into a cognitive state.

    Parameters
    ----------
    mean_pred : np.ndarray
        Shape (20484,) — mean predicted fMRI activity across time segments.

    Returns
    -------
    dict with keys: focus_state, confidence, active_networks, details
    """
    # 1. Compute activation score for each functional network
    network_scores = {}
    for network_name, info in FOCUS_REGIONS.items():
        try:
            indices = get_hcp_roi_indices(info["rois"], mesh="fsaverage5")
            activation = mean_pred[indices].mean()
            network_scores[network_name] = float(activation)
        except ValueError:
            # Some ROI names may not match exactly — use wildcard
            network_scores[network_name] = 0.0

    # 2. Compute composite scores for each cognitive state
    focus_score = np.mean([
        network_scores.get("prefrontal", 0),
        network_scores.get("dlpfc", 0),
        network_scores.get("ips_attention", 0),
        network_scores.get("language_processing", 0),
    ])

    lure_score = np.mean([
        network_scores.get("visual_salience", 0),
        network_scores.get("ventral_attention", 0),
        network_scores.get("reward_emotional", 0),
        network_scores.get("auditory_engagement", 0) * 0.5, # Slightly weights audio towards lured if not educational
    ])

    distraction_score = network_scores.get("default_mode", 0)

    # 3. Determine dominant state
    scores = {
        "focused": float(focus_score),
        "lured": float(lure_score),
        "distracted": float(distraction_score),
    }
    focus_state = max(scores, key=scores.get)

    # 4. Compute a relative confidence
    total = sum(abs(v) for v in scores.values()) or 1
    confidence = abs(scores[focus_state]) / total

    return {
        "focus_state": focus_state,
        "confidence": round(confidence, 3),
        "scores": {k: round(v, 4) if not np.isnan(v) else 0.0 for k, v in scores.items()},
        "top_active_regions": get_topk_rois(mean_pred, k=10, mesh="fsaverage5").tolist(),
        "network_activations": {k: round(v, 4) if not np.isnan(v) else 0.0 for k, v in network_scores.items()},
    }
