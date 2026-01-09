
import pytest
import pandas as pd
from io import StringIO
from core.schema_builder import infer_schema_from_csv, FieldType

def test_infer_schema_simple():
    csv_data = """Meta Info
Title,Cases,Is_Smoker,Age,Description
"Study A",10,1,55,"A detailed study"
"Study B",5,0,42,"Another study"
"""
    # Create a dummy CSV file
    csv_file = StringIO(csv_data)
    
    # We need to mock pandas.read_csv to accept StringIO or write to a temp file
    # Ideally, the function takes a file path. Let's write to a temp file.
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp.write(csv_data)
        tmp_path = tmp.name
        
    try:
        fields = infer_schema_from_csv(tmp_path)
        
        # Verify fields
        field_map = {f.name: f for f in fields}
        
        assert "title" in field_map
        assert field_map["title"].field_type == FieldType.TEXT
        
        assert "cases" in field_map
        assert field_map["cases"].field_type == FieldType.INTEGER
        
        assert "is_smoker" in field_map
        # Heuristic: 0/1 columns might be Integer or Boolean, 
        # but our plan said "Use FieldType.INTEGER for binary flags (0/1)"
        assert field_map["is_smoker"].field_type == FieldType.INTEGER 
        
        assert "age" in field_map
        assert field_map["age"].field_type == FieldType.INTEGER
        
        assert "description" in field_map
        assert field_map["description"].field_type == FieldType.TEXT
        
    finally:
        os.remove(tmp_path)

def test_infer_schema_with_floats_and_nan():
    csv_data = """Meta Info
Metric_A,Metric_B,Notes
1.5,10,
2.5,,
,30,"Some notes"
"""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp.write(csv_data)
        tmp_path = tmp.name
        
    try:
        fields = infer_schema_from_csv(tmp_path)
        field_map = {f.name: f for f in fields}
        
        assert field_map["metric_a"].field_type == FieldType.FLOAT
        assert field_map["metric_b"].field_type == FieldType.INTEGER # Should handle optional ints if pandas handles it
        assert field_map["notes"].field_type == FieldType.TEXT
        
    finally:
        os.remove(tmp_path)
