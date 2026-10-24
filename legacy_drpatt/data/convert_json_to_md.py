import json
import os
import re

# กำหนดพาธของโฟลเดอร์ผลลัพธ์
BASE_DIR = "/media/tanchon-lita/Data/Pr/dr_pat/data"
OUTPUT_DIR = os.path.join(BASE_DIR, "tspi_markdown")
AXES_DIR = os.path.join(OUTPUT_DIR, "axes")
PRODUCTS_DIR = os.path.join(OUTPUT_DIR, "products")

# สร้างโฟลเดอร์ถ้ายังไม่มี
os.makedirs(AXES_DIR, exist_ok=True)
os.makedirs(PRODUCTS_DIR, exist_ok=True)

print("="*60)
print("🛠️ TSPI™ JSON to Markdown Exporter v1.0")
print("="*60)

def clean_filename(name):
    name_str = str(name or "N_A")
    # ลบอักขระที่ไม่เป็นมิตรกับชื่อไฟล์
    cleaned = re.sub(r'[^a-zA-Z0-9ก-๙\s_\-]', '', name_str)
    # เปลี่ยนเว้นวรรคเป็น underscore
    return re.sub(r'\s+', '_', cleaned.strip())

# ============================================================
# ส่วนที่ 1: แปลง 39 แกนชีววิทยา (39_last_x.json)
# ============================================================
axes_file_path = os.path.join(BASE_DIR, "39_last_x.json")
if os.path.exists(axes_file_path):
    print("⏳ กำลังโหลดและแปลง 39 แกนชีววิทยา (39_last_x.json)...")
    with open(axes_file_path, "r", encoding="utf-8") as f:
        axes_data = json.load(f)
    
    total_axes_created = 0
    
    for domain in axes_data.get("domains", []):
        domain_id = domain.get("domain_id")
        domain_title = domain.get("title")
        
        for axis in domain.get("axes", []):
            axis_id = axis.get("axis_id")
            axis_name = axis.get("name")
            sub_axes = axis.get("sub_axes", {})
            modules = axis.get("modules", [])
            modules_by_context = axis.get("modules_by_context", {})
            
            # สร้างหน้าเนื้อหา Markdown ของแต่ละแกนแบบละเอียด
            md_content = f"""# 🩺 TSPI Biological Axis: Axis {axis_id} - {axis_name}

## 📊 ข้อมูลทั่วไปของแกน
*   **หมายเลขแกน (Axis ID):** Axis {axis_id}
*   **ชื่อแกน (Axis Name):** {axis_name}
*   **โดเมนหลัก (Domain):** Domain {domain_id} - {domain_title}

---

## 🧬 แกนย่อย (Sub-Axes) และคำอธิบายกลไก
"""
            
            if sub_axes:
                for sub_id, sub_info in sub_axes.items():
                    sub_name = sub_info.get("name", "N/A")
                    sub_desc = sub_info.get("description", "N/A")
                    md_content += f"""### แกนย่อย {axis_id}{sub_id}: {sub_name}
*   **คำอธิบายกลไก:** {sub_desc}

"""
            else:
                md_content += "*ไม่มีข้อมูลแกนย่อยเพิ่มเติม*\n\n"
                
            md_content += "---\n\n## 🛠️ โมดูลและกฎทางคลินิกอ้างอิง (Clinical Contexts)\n"
            
            if modules_by_context:
                for context, rules in modules_by_context.items():
                    md_content += f"### บริบท: {context}\n"
                    if isinstance(rules, list):
                        for rule in rules:
                            md_content += f"*   {rule}\n"
                    elif isinstance(rules, dict):
                        for k, v in rules.items():
                            md_content += f"*   **{k}:** {v}\n"
                    else:
                        md_content += f"*   {rules}\n"
                    md_content += "\n"
            elif modules:
                md_content += "### รายการโมดูลการประเมิน:\n"
                for mod in modules:
                    md_content += f"*   {mod}\n"
            else:
                md_content += "*ไม่มีข้อมูลโมดูลทางคลินิกกำกับเฉพาะเจาะจงในขณะนี้*\n"
                
            # บันทึกลงไฟล์
            safe_name = clean_filename(axis_name)
            filename = f"axis_{axis_id:02d}_{safe_name}.md"
            file_path = os.path.join(AXES_DIR, filename)
            
            with open(file_path, "w", encoding="utf-8") as out:
                out.write(md_content)
            
            total_axes_created += 1
            
    print(f"✅ แปลง 39 แกนชีววิทยาสำเร็จ! สร้างไฟล์สำเร็จ {total_axes_created} ไฟล์ ที่: {AXES_DIR}")
else:
    print("❌ ไม่พบไฟล์ 39_last_x.json ในโฟลเดอร์ data!")

# ============================================================
# ส่วนที่ 2: แปลง 200 โมดูลรักษา/สมุนไพร (200_module_tspi.json)
# ============================================================
modules_file_path = os.path.join(BASE_DIR, "200_module_tspi.json")
if os.path.exists(modules_file_path):
    print("\n⏳ กำลังโหลดและแปลง 200 โมดูลการรักษา/สมุนไพร (200_module_tspi.json)...")
    with open(modules_file_path, "r", encoding="utf-8") as f:
        modules_data = json.load(f)
        
    total_products_created = 0
    
    for item in modules_data.get("data", []):
        raw_prod_id = item.get("Code /_Product ID")
        if raw_prod_id is None:
            continue
        prod_id = str(raw_prod_id).strip()
        if not prod_id:
            continue
        phyto_code = item.get("PhytoCore Code", "N/A")
        prod_name = item.get("Product Derived From", "N/A")
        composition = item.get("Botanical Composition", "N/A")
        function = item.get("Mechanistic Function", "N/A")
        bioactive = item.get("Key Bioactive Markers_(LC-MS)", "N/A")
        axis_mapping = item.get("TSPI Axis Mapping", "N/A")
        cytotoxicity = item.get("Cytotoxicity", "N/A")
        ld50 = item.get("LD50 Animal", "N/A")
        proteomics = item.get("Proteomics Marker /_Efficacy Pathway", "N/A")
        peak_ratio = item.get("Peak Ratio Active_Substances", "N/A")
        node_diseases = item.get("Node Diseases /_Effective Score", "N/A")
        pillars = item.get("Main Key Mechanism_(3 Pillars)", "N/A")
        risk_score = item.get("Drug-Herb Interaction_Risk Score", "N/A")
        biomarker = item.get("Biomarker Response", "N/A")
        dose = item.get("Recommended Dose /_Treatment Duration", "N/A")
        category = item.get("Health Category", "N/A")
        taste_energy = item.get("Taste-Energy_(The taste of medicine)", "N/A")
        
        # กรองข้อมูลพิเศษอื่นๆ
        safety = item.get("Safety Profile")
        research = item.get("Research Status")
        summary_bio = item.get("Summary of Biological Activity")
        antioxidant = item.get("Antioxidant Activity")
        selectivity_idx = item.get("Selectivity Index")
        gut_metabolic = item.get("Gut-Metabolic Concept")
        interpretation = item.get("Interpretation")
        
        # จัดรูปแบบไฟล์ Markdown แยกทีละโปรดักส์แบบละเอียดยิบ
        md_content = f"""# 🌿 TSPI Clinical Herb Module: {prod_id} - {prod_name}

## 📋 ข้อมูลระบุตัวตน (Identification)
*   **รหัสสมุนไพร/ตำรับ (Product ID):** {prod_id}
*   **รหัสไฟโตคอร์ (PhytoCore Code):** {phyto_code}
*   **ชื่อสามัญ/ชื่อทางการค้า (Product Name):** {prod_name}
*   **หมวดหมู่สุขภาพ (Health Category):** {category}
*   **รสและพลังงานยา (Taste & Energy):** {taste_energy}

---

## 🔬 กลไกการออกฤทธิ์ทางชีววิทยา (Mechanistic Activity)
### 1. องค์ประกอบพฤกษเคมี (Botanical Composition)
{composition}

### 2. หน้าที่เชิงกลไกชีวภาพ (Mechanistic Function)
{function}

### 3. สารบ่งชี้ชีวภาพหลัก (Key Bioactive Markers LC-MS)
`{bioactive}`

### 4. เส้นทางโปรตีโอมิกส์ (Proteomics Pathways & Efficacy)
{proteomics}

### 5. สัดส่วนสารสำคัญสูงสุด (Peak Active Substance Ratios)
{peak_ratio}

### 6. กลไกหลัก 3 เสาหลัก (Main 3 Pillars Mechanism)
{pillars}

---

## 🎯 แผนที่การเชื่อมโยงระบบชีวภาพ (TSPI Bio-Axis Mapping)
*   **แกนชีววิทยาที่เกี่ยวข้อง (Axis Mapping):** 
    {axis_mapping}

---

## 🩺 ข้อบ่งชี้และการรักษาทางคลินิก (Clinical Indications & Dosage)
*   **โรคและอาการที่ตอบสนองได้ดี (Effective Node Diseases):** {node_diseases}
*   **การตอบสนองของตัวบ่งชี้ชีวภาพ (Biomarker Response):** {biomarker}
*   **ปริมาณและระยะเวลาแนะนำ (Recommended Dose & Duration):** {dose}
*   **ความเสี่ยงการตีกันกับยาแผนปัจจุบัน (Drug-Herb Interaction Risk):** {risk_score}

---

## 🛡️ ข้อมูลความปลอดภัยและความเป็นพิษ (Safety & Toxicity Profile)
*   **ความเป็นพิษต่อเซลล์ (Cytotoxicity):** {cytotoxicity}
*   **ค่าความปลอดภัยสัตว์ทดลอง (LD50 Animal):** {ld50}
"""

        # เพิ่มฟิลด์เสริมหากมีข้อมูล
        if safety:
            md_content += f"*   **โปรไฟล์ความปลอดภัย (Safety Profile):** {safety}\n"
        if research:
            md_content += f"*   **สถานะงานวิจัย (Research Status):** {research}\n"
        if summary_bio:
            md_content += f"\n### สรุปฤทธิ์ทางชีวภาพ (Summary of Biological Activity)\n{summary_bio}\n"
        if antioxidant:
            md_content += f"*   **ฤทธิ์ต้านอนุมูลอิสระ (Antioxidant Activity):** {antioxidant}\n"
        if selectivity_idx:
            md_content += f"*   **ดัชนีการเลือกทำลาย (Selectivity Index):** {selectivity_idx}\n"
        if gut_metabolic:
            md_content += f"\n### แนวคิดระบบทางเดินอาหารและเผาผลาญ (Gut-Metabolic Concept)\n{gut_metabolic}\n"
        if interpretation:
            md_content += f"\n### การตีความผลการรักษา (Interpretation)\n{interpretation}\n"

        # บันทึกลงไฟล์
        safe_name = clean_filename(prod_name)
        filename = f"product_{prod_id.replace('/', '_')}_{safe_name}.md"
        file_path = os.path.join(PRODUCTS_DIR, filename)
        
        with open(file_path, "w", encoding="utf-8") as out:
            out.write(md_content)
            
        total_products_created += 1
        
    print(f"✅ แปลง 200 โมดูลสำเร็จ! สร้างไฟล์สำเร็จ {total_products_created} ไฟล์ ที่: {PRODUCTS_DIR}")
else:
    print("❌ ไม่พบไฟล์ 200_module_tspi.json ในโฟลเดอร์ data!")

print("\n" + "="*60)
print("🎉 การแปลงข้อมูลจาก JSON เป็น Markdown เสร็จสมบูรณ์แล้ว!")
print(f"📂 โฟลเดอร์หลัก: {OUTPUT_DIR}")
print(f"📂 แกนชีววิทยา: {total_axes_created} ไฟล์")
print(f"📂 ผลิตภัณฑ์/โมดูลสมุนไพร: {total_products_created} ไฟล์")
print("="*60)
