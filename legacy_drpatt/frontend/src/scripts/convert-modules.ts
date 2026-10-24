import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';

const csvFilePath = '/media/tanchon-lita/Data/Pr/dr_pat/data/200 module tspi 2 (24-4-69).csv';
const outputFilePath = '/media/tanchon-lita/Data/Pr/dr_pat/frontend/src/data/modules_db.json';

function convertCsvToJson() {
  const fileContent = fs.readFileSync(csvFilePath, { encoding: 'utf-8' });
  
  // Skip first row if it's the title row, then headers are on row 2 (index 1)
  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
    from_line: 2 // Assuming headers are on line 2 based on head output
  });

  const modules = records.map((row: any) => {
    // Parse Axis Mapping
    const mappingRaw = row['TSPI Axis Mapping'] || '';
    const axes = mappingRaw.split('\n').map((a: string) => a.trim()).filter(Boolean);

    return {
      id: row['Code / '] || row['PhytoCore Code'],
      name: row['Product Derived From'],
      mechanism: row['Mechanistic Function'],
      markers: row['Key Bioactive Markers '],
      axes: axes,
      dosage: row['Recommended Dose / '],
      category: row['Health Category'],
      safety: row['Safety Profile']
    };
  });

  fs.writeFileSync(outputFilePath, JSON.stringify(modules, null, 2));
  console.log(`✅ Converted ${modules.length} modules to JSON.`);
}

convertCsvToJson();
