import json
import os
import re

source_path = '/Users/tanchonl/Downloads/drpatt/data/last_dta/200_module_tspi.json'
dest_path = '/Users/tanchonl/Downloads/drpatt/frontend/src/data/modules_db.json'

def main():
    if not os.path.exists(source_path):
        print(f"Error: Source file {source_path} not found.")
        return

    with open(source_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modules = []
    for row in data.get('data', []):
        axes_str = row.get('TSPI Axis Mapping') or ''
        # Extract axis numbers using regex e.g. "Axis 1 - ..." -> 1
        numbers = [int(n) for n in re.findall(r'Axis\s+(\d+)', axes_str, re.IGNORECASE)]
        
        modules.append({
            "id": row.get("Code /_Product ID") or row.get("PhytoCore Code"),
            "name": row.get("Product Derived From") or row.get("Botanical Composition"),
            "module_code": row.get("PhytoCore Code"),
            "mechanism": row.get("Mechanistic Function"),
            "markers": row.get("Key Bioactive Markers_(LC-MS)"),
            "axes": numbers,
            "tspi_axis_mapping": axes_str,
            "dosage": row.get("Recommended Dose / _Treatment Duration"),
            "category": row.get("Health Category"),
            "safety": row.get("Safety Profile")
        })

    with open(dest_path, 'w', encoding='utf-8') as f:
        json.dump(modules, f, indent=2, ensure_ascii=False)

    print(f"Successfully converted {len(modules)} modules to {dest_path}")

if __name__ == '__main__':
    main()
