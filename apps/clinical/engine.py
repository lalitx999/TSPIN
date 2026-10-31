"""
TSPI 39 Biological Axes Engine & Knowledge Graph Service (EP 4).
Loads and indexes the 12 Domains, 39 Axes, Network Topology, and 200 Therapeutic Modules.
"""

import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Any, Optional

DATA_DIR = Path(__file__).resolve().parent / 'data'

class TspiClinicalEngine:
    """
    คลาสบริการกลางสำหรับกลไก 39 แกนชีววิทยา (Mechanistic Biological Engine)
    ทำหน้าที่ประมวลผลคะแนน เชื่อมโยงเครือข่ายชีวภาพ และจับคู่โมดูลการรักษา
    """
    _axes_cache = None
    _modules_cache = None
    _network_cache = None

    @classmethod
    def get_axes_data(cls) -> Dict[str, Any]:
        """โหลดข้อมูล 12 Domains และ 39 Axes พร้อม Cache ในหน่วยความจำ"""
        if cls._axes_cache is None:
            file_path = DATA_DIR / 'tspi_39_axes.json'
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    cls._axes_cache = json.load(f)
            else:
                cls._axes_cache = {'domains': [], 'total_axes': 39}
        return cls._axes_cache

    @classmethod
    def get_modules_data(cls) -> List[Dict[str, Any]]:
        """โหลดข้อมูล 200 โมดูลสารอาหารและสารพฤกษเคมีบำบัด (Therapeutic Modules)"""
        if cls._modules_cache is None:
            file_path = DATA_DIR / '200_module_tspi.json'
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    items = []
                    if isinstance(raw, dict) and 'data' in raw:
                        items = raw['data']
                    elif isinstance(raw, list):
                        items = raw
                    
                    # Normalize common fields for template and matching convenience
                    normalized = []
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        mod = dict(item)
                        mod['code'] = mod.get('code') or mod.get('PhytoCore Code') or mod.get('Code /_Product ID') or 'MOD'
                        mod['name'] = mod.get('name') or mod.get('Product Derived From') or mod.get('Botanical Composition') or 'Therapeutic Module'
                        mod['description'] = mod.get('description') or mod.get('Main Key Mechanism_(3 Pillars)') or mod.get('Mechanistic Function') or ''
                        normalized.append(mod)
                    cls._modules_cache = normalized
            else:
                cls._modules_cache = []
        return cls._modules_cache

    @classmethod
    def get_network_data(cls) -> Dict[str, Any]:
        """โหลดแผนผังเครือข่ายชีวภาพ (180 Biological Network Topology)"""
        if cls._network_cache is None:
            file_path = DATA_DIR / '180_network.json'
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    cls._network_cache = json.load(f)
            else:
                cls._network_cache = {'nodes': [], 'links': []}
        return cls._network_cache

    @classmethod
    def get_all_axes(cls) -> List[Dict[str, Any]]:
        """ส่งกลับรายการทั้ง 39 แกนแบบ Flat List พร้อมชื่อโดเมนกำกับ"""
        data = cls.get_axes_data()
        all_axes = []
        for domain in data.get('domains', []):
            dom_id = domain.get('domain_id')
            dom_title = domain.get('title')
            for ax in domain.get('axes', []):
                ax_copy = dict(ax)
                ax_copy['domain_id'] = dom_id
                ax_copy['domain_title'] = dom_title
                all_axes.append(ax_copy)
        return sorted(all_axes, key=lambda x: x.get('axis_id', 0))

    @classmethod
    def get_axis_by_id(cls, axis_id: int) -> Optional[Dict[str, Any]]:
        """ค้นหาข้อมูลของแกนใดแกนหนึ่งจาก Axis ID (1 - 39)"""
        for ax in cls.get_all_axes():
            if ax.get('axis_id') == axis_id:
                return ax
        return None

    @classmethod
    def get_domains_with_axes(cls) -> List[Dict[str, Any]]:
        """ส่งกลับโครงสร้างทั้ง 12 โดเมนพร้อมแกนย่อยในแต่ละโดเมน"""
        return cls.get_axes_data().get('domains', [])

    @classmethod
    def calculate_domain_scores(cls, scores_dict: Dict[int, int]) -> List[Dict[str, Any]]:
        """
        รวมคะแนนเฉลี่ยในแต่ละโดเมนทั้ง 12 โดเมน สำหรับเรดาร์ชาร์ตระดับโดเมน (Domain-level Radar)
        """
        domains = cls.get_domains_with_axes()
        domain_scores = []
        for dom in domains:
            dom_axes = dom.get('axes', [])
            if not dom_axes:
                continue
            # เฉลี่ยเฉพาะแกนที่ประเมินแล้ว แกนที่ยังไม่มีผลไม่นับเป็น 50
            scored = [scores_dict.get(ax.get('axis_id')) for ax in dom_axes]
            scored = [v for v in scored if v is not None]
            avg = round(sum(scored) / len(scored), 1) if scored else None
            domain_scores.append({
                'domain_id': dom.get('domain_id'),
                'title': dom.get('title'),
                'average_score': avg,
                'axes_count': len(dom_axes),
                'scored_axes_count': len(scored),
            })
        return domain_scores

    @classmethod
    def match_therapeutic_recommendations(cls, dysfunctional_axes: List[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
        """
        ค้นหาและจับคู่โมดูลการรักษาจาก 200_module_tspi.json สำหรับแกนที่มีปัญหา
        """
        modules = cls.get_modules_data()
        if not modules or not dysfunctional_axes:
            return []

        target_axis_ids = {item['axis_id'] for item in dysfunctional_axes}
        matched = []

        # สแกนโมดูลที่เกี่ยวข้องกับแกนเป้าหมาย
        for mod in modules:
            mod_axes = mod.get('axes', []) or mod.get('target_axes', [])
            # ตรวจสอบว่าโมดูลมีแกนตรงกับแกนที่มีปัญหาหรือไม่
            has_match = False
            mapping_text = str(mod.get('TSPI Axis Mapping', '') or '')
            for tid in target_axis_ids:
                if f"Axis {tid} " in mapping_text or f"Axis {tid} –" in mapping_text or f"Axis {tid}:" in mapping_text or f"Axis {tid}-" in mapping_text:
                    has_match = True
                    break

            if not has_match and isinstance(mod_axes, list):
                for ax_val in mod_axes:
                    if isinstance(ax_val, int) and ax_val in target_axis_ids:
                        has_match = True
                        break
                    elif isinstance(ax_val, str) and any(f"AXIS_{tid}" in ax_val for tid in target_axis_ids):
                        has_match = True
                        break

            if has_match:
                matched.append(mod)
                if len(matched) >= limit:
                    break

        # หากยังไม่ครบ limit ให้ดึงโมดูลพื้นฐานเสริม
        if len(matched) < limit and modules:
            for mod in modules:
                if mod not in matched:
                    matched.append(mod)
                if len(matched) >= limit:
                    break

        return matched
