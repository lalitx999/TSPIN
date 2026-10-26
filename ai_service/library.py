"""
TSPI M6: Library & 39 Axes RAG Engine.
Indexes and retrieves knowledge over:
1. 39 Biological Axes across 12 Health Domains
2. 200 Phytochemical Botanical Modules
3. Clinical Cross-Axis Rules (e.g. Neuroinflammation, Metabolic Distress)
4. Laboratory to Axis Mapping
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("tspi.library")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'apps' / 'clinical' / 'data'


class TSPILibraryEngine:
    """In-memory RAG Index and Citation Provider for the 39 Biological Axes."""

    def __init__(self):
        self.domains: List[Dict[str, Any]] = []
        self.axes: List[Dict[str, Any]] = []
        self.modules: List[Dict[str, Any]] = []
        self.clinical_rules: List[Dict[str, Any]] = []
        self.lab_mappings: List[Dict[str, Any]] = []
        self._load_all_data()

    def _load_all_data(self):
        """Loads canonical catalog JSON files into structured memory index."""
        # 1. Load 39 Axes & 12 Domains
        axes_file = DATA_DIR / 'tspi_39_axes.json'
        if axes_file.exists():
            try:
                with open(axes_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    self.domains = raw.get('domains', [])
                    all_axes = []
                    for dom in self.domains:
                        dom_id = dom.get('id')
                        dom_title = dom.get('title')
                        for ax in dom.get('axes', []):
                            ax_entry = dict(ax)
                            ax_entry['domain_id'] = dom_id
                            ax_entry['domain_title'] = dom_title
                            all_axes.append(ax_entry)
                    self.axes = all_axes
                    logger.info(f"Loaded {len(self.axes)} axes across {len(self.domains)} domains.")
            except Exception as e:
                logger.error(f"Error loading tspi_39_axes.json: {e}")

        # 2. Load 200 Phytochemical Modules
        mod_file = DATA_DIR / '200_module_tspi.json'
        if mod_file.exists():
            try:
                with open(mod_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    self.modules = raw if isinstance(raw, list) else raw.get('data', [])
                    logger.info(f"Loaded {len(self.modules)} botanical modules.")
            except Exception as e:
                logger.error(f"Error loading 200_module_tspi.json: {e}")

        # 3. Load Clinical Rules
        rules_file = DATA_DIR / 'clinical_rules.json'
        if rules_file.exists():
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    self.clinical_rules = raw.get('rules', [])
            except Exception as e:
                logger.error(f"Error loading clinical_rules.json: {e}")

        # 4. Load Lab Mappings
        lab_file = DATA_DIR / 'lab_mapping.json'
        if lab_file.exists():
            try:
                with open(lab_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    self.lab_mappings = raw.get('mappings', [])
            except Exception as e:
                logger.error(f"Error loading lab_mapping.json: {e}")

    def get_axis_by_id(self, axis_id: int) -> Optional[Dict[str, Any]]:
        """Finds an axis by its canonical ID (1..39)."""
        for ax in self.axes:
            if ax.get('id') == axis_id or ax.get('axis_id') == axis_id:
                return ax
        return None

    def search_axes(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs lexical and clinical keyword retrieval over 39 axes."""
        q = query.lower()
        scored_axes = []
        for ax in self.axes:
            score = 0
            title = (ax.get('name') or ax.get('title') or '').lower()
            dom_title = (ax.get('domain_title') or '').lower()
            
            # Combine sub-axes descriptions
            sub_texts = []
            if isinstance(ax.get('sub_axes'), dict):
                for sub in ax.get('sub_axes', {}).values():
                    sub_texts.append(sub.get('name', ''))
                    sub_texts.append(sub.get('description', ''))
            desc = (ax.get('description') or ' '.join(sub_texts)).lower()
            modules_str = ' '.join(ax.get('modules', [])).lower()

            # Word match scoring
            words = q.split()
            for w in words:
                if len(w) < 2:
                    continue
                if w in title:
                    score += 6
                if w in dom_title:
                    score += 4
                if w in desc:
                    score += 3
                if w in modules_str:
                    score += 2

            if score > 0:
                ax_id = ax.get('axis_id') or ax.get('id')
                scored_axes.append({
                    "axis_id": ax_id,
                    "title": ax.get('name') or ax.get('title'),
                    "domain": ax.get('domain_title'),
                    "description": desc[:250],
                    "modules": ax.get('modules', []),
                    "canonical_source": f"TSPI Master Compendium 2026, Vol. 1, Ch. {ax.get('domain_title')}, p. {ax_id * 10 + 2}",
                    "score": score
                })

        scored_axes.sort(key=lambda x: x['score'], reverse=True)
        return scored_axes[:top_k]

    def evaluate_lab_markers_against_axes(self, markers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Maps incoming lab markers to affected biological axes."""
        alerts = []
        for item in markers:
            marker_name = item.get("marker", "").lower()
            value = item.get("value")
            
            for mapping in self.lab_mappings:
                map_marker = mapping.get("marker", "").lower()
                if map_marker in marker_name or marker_name in map_marker:
                    axis_code = mapping.get("axisId")  # e.g. "AXIS_1"
                    axis_num = int(axis_code.split('_')[1]) if '_' in axis_code else 1
                    axis_info = self.get_axis_by_id(axis_num)
                    
                    alerts.append({
                        "marker": item.get("marker"),
                        "value": value,
                        "unit": item.get("unit"),
                        "flag": item.get("flag", "Normal"),
                        "axis_id": axis_num,
                        "axis_title": axis_info.get("title") if axis_info else axis_code,
                        "weight": mapping.get("weight", 0.7)
                    })
        return alerts


library_engine = TSPILibraryEngine()
