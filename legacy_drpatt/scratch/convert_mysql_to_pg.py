"""
Enhanced MySQL to PostgreSQL SQL Dump Converter
Strips ALL MySQL-specific ALTER TABLE ... MODIFY statements across newlines.
"""
import re
import sys
import os

def convert_sql(input_file, output_file):
    print(f"🔄 Converting {input_file} to clean PostgreSQL format...")
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 1. Remove MySQL specific headers and comments
    content = re.sub(r'/\*![\s\S]*?\*/;', '', content)
    content = re.sub(r'/\*![\s\S]*?\*/', '', content)
    content = re.sub(r'SET SQL_MODE[\s\S]*?;', '', content)
    content = re.sub(r'SET time_zone[\s\S]*?;', '', content)
    content = re.sub(r'LOCK TABLES[\s\S]*?;', '', content)
    content = re.sub(r'UNLOCK TABLES;', '', content)

    # 2. Strip ALL ALTER TABLE ... MODIFY statements (phpMyAdmin AUTO_INCREMENT section at bottom)
    content = re.sub(r'ALTER\s+TABLE\s+`[^`]+`[\s\S]*?MODIFY[\s\S]*?;', '', content, flags=re.IGNORECASE)

    # 3. Replace backticks with double quotes
    content = re.sub(r'`([^`]+)`', r'"\1"', content)

    # 4. Replace Engine and Table Options
    content = re.sub(r'ENGINE=InnoDB[\s\S]*?;', ';', content)
    content = re.sub(r'ENGINE=MyISAM[\s\S]*?;', ';', content)
    content = re.sub(r'DEFAULT CHARSET=[\w]+\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'COLLATE=[\w]+\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'AUTO_INCREMENT=\d+\s*', '', content, flags=re.IGNORECASE)

    # 5. Replace Data Types
    content = re.sub(r'\bint\(\d+\)\s+NOT\s+NULL\s+AUTO_INCREMENT\b', 'SERIAL PRIMARY KEY', content, flags=re.IGNORECASE)
    content = re.sub(r'\bbigint\(\d+\)\s+NOT\s+NULL\s+AUTO_INCREMENT\b', 'BIGSERIAL PRIMARY KEY', content, flags=re.IGNORECASE)
    content = re.sub(r'\bint\(\d+\)', 'integer', content, flags=re.IGNORECASE)
    content = re.sub(r'\bbigint\(\d+\)', 'bigint', content, flags=re.IGNORECASE)
    content = re.sub(r'\btinyint\(1\)', 'boolean', content, flags=re.IGNORECASE)
    content = re.sub(r'\btinyint\(\d+\)', 'smallint', content, flags=re.IGNORECASE)
    content = re.sub(r'\bmediumtext\b', 'text', content, flags=re.IGNORECASE)
    content = re.sub(r'\blongtext\b', 'text', content, flags=re.IGNORECASE)
    content = re.sub(r'\btinytext\b', 'text', content, flags=re.IGNORECASE)
    content = re.sub(r'\bdatetime\b', 'timestamp', content, flags=re.IGNORECASE)
    content = re.sub(r'\bdouble\b', 'double precision', content, flags=re.IGNORECASE)
    content = re.sub(r'\bunsigned\b', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\benum\([\s\S]*?\)', 'varchar(255)', content, flags=re.IGNORECASE)

    # 6. Escapes
    content = content.replace("\\'", "''")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Successfully converted to {output_file} ({os.path.getsize(output_file)} bytes)")

if __name__ == "__main__":
    src = "/Users/tanchonl/Downloads/drpatt/backend/u239440273_drpatrcl_sys_fixed.sql"
    dst = "/Users/tanchonl/Downloads/drpatt/backend/u239440273_drpatrcl_sys_pg.sql"
    convert_sql(src, dst)
