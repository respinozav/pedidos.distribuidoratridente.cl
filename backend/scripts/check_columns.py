import sys
import os
sys.path.insert(0, os.path.abspath("backend"))
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    cols = conn.execute(text("""
        SELECT column_name, data_type, character_maximum_length 
        FROM information_schema.columns 
        WHERE table_schema = 'bdtridente' AND table_name = 'publicidades' 
        ORDER BY ordinal_position;
    """)).fetchall()
    print("Columnas en bdtridente.publicidades:")
    for c in cols:
        print(f" - {c[0]}: {c[1]} (max_len={c[2]})")
