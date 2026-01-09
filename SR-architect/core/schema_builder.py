#!/usr/bin/env python3
"""
Dynamic Pydantic Schema Builder for user-defined extraction variables.

Creates Pydantic models at runtime based on user input.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Type, get_type_hints, Union, Annotated
from pydantic import BaseModel, Field, create_model, BeforeValidator
from pydantic import BaseModel, Field, create_model, BeforeValidator
from enum import Enum
import pandas as pd
import re


class FieldType(str, Enum):
    """Supported field types for extraction."""
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST_TEXT = "list_text"


def ensure_list(v: Any) -> List[str]:
    """Coerce value to list of strings."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(i) for i in v]
    return [str(v)]

def ensure_int(v: Any) -> Optional[int]:
    """Coerce value to integer."""
    if v is None:
        return None
    if isinstance(v, list):
        if not v:
            return None
        return int(v[0]) # Take first item
    try:
        return int(v)
    except (ValueError, TypeError):
        return None

def ensure_str(v: Any) -> Optional[str]:
    """Coerce value to string."""
    if v is None:
        return None
    if isinstance(v, list):
        if not v:
            return None
        # Join multiple strings if list is provided (common for quotes)
        return " ".join([str(i) for i in v])
    return str(v)

# Flexible types
FlexibleList = Annotated[List[str], BeforeValidator(ensure_list)]
FlexibleInt = Annotated[Optional[int], BeforeValidator(ensure_int)]
FlexibleStr = Annotated[Optional[str], BeforeValidator(ensure_str)]


@dataclass
class FieldDefinition:
    """Definition of a field to extract."""
    name: str
    description: str
    field_type: FieldType = FieldType.TEXT
    required: bool = True
    include_quote: bool = True  # Include source quote for traceability



def get_python_type(field_type: FieldType) -> type:
    """Map FieldType to Python type."""
    mapping = {
        FieldType.TEXT: FlexibleStr,
        FieldType.INTEGER: FlexibleInt,
        FieldType.FLOAT: float, # Could make FlexibleFloat too
        FieldType.BOOLEAN: bool,
        FieldType.LIST_TEXT: FlexibleList,
    }
    return mapping.get(field_type, FlexibleStr)


def build_extraction_model(
    fields: List[FieldDefinition],
    model_name: str = "DynamicExtractionModel"
) -> Type[BaseModel]:
    """
    Build a Pydantic model dynamically from field definitions.
    
    For each field with include_quote=True, a companion "_quote" field is added
    for citation traceability.
    
    Args:
        fields: List of field definitions
        model_name: Name for the generated model class
        
    Returns:
        Dynamically created Pydantic model class
    """
    field_definitions = {}
    
    for field_def in fields:
        python_type = get_python_type(field_def.field_type)
        # Note: Flexible types are already Optional-ish due to logic, 
        # but we keep the structure for consistency.
        
        # Always allow None/Null for LLM extraction robustness
        python_type = Optional[python_type]
        
        # Handle optional fields (Key presence)
        if not field_def.required:
            default = None
        else:
            default = ...  # Required field marker (Key must be present in JSON)
        
        # Main field
        field_definitions[field_def.name] = (
            python_type,
            Field(
                default=default,
                description=field_def.description,
            )
        )
        
        # Quote field for traceability
        if field_def.include_quote:
            quote_field_name = f"{field_def.name}_quote"
            # Use FlexibleStr for quotes as models often return lists of quotes
            field_definitions[quote_field_name] = (
                FlexibleStr,
                Field(
                    default=None,
                    description=f"Exact quote from text supporting the {field_def.name} value",
                )
            )
    
    # Add standard metadata fields
    field_definitions["filename"] = (
        FlexibleStr,
        Field(default=None, description="Source filename")
    )
    field_definitions["extraction_confidence"] = (
        Optional[float],
        Field(default=None, description="Model's confidence in extraction (0-1)")
    )
    field_definitions["extraction_notes"] = (
        Optional[str],
        Field(default=None, description="Any notes or uncertainties about extraction")
    )
    
    # Create the model
    DynamicModel = create_model(model_name, **field_definitions)
    
    return DynamicModel


# Pre-defined schemas for common systematic review types

def get_rct_schema() -> List[FieldDefinition]:
    """Schema for Randomized Controlled Trials."""
    return [
        FieldDefinition("study_design", "Type of study (RCT, quasi-RCT, etc.)", FieldType.TEXT),
        FieldDefinition("sample_size", "Total number of participants randomized", FieldType.INTEGER),
        FieldDefinition("population", "Description of study population/patients", FieldType.TEXT),
        FieldDefinition("intervention", "Description of the intervention/treatment", FieldType.TEXT),
        FieldDefinition("comparator", "Description of control/comparator group", FieldType.TEXT),
        FieldDefinition("primary_outcome", "Primary outcome measure", FieldType.TEXT),
        FieldDefinition("primary_result", "Result for primary outcome", FieldType.TEXT),
        FieldDefinition("adverse_events", "Reported adverse events", FieldType.LIST_TEXT, required=False),
        FieldDefinition("follow_up_duration", "Duration of follow-up", FieldType.TEXT),
        FieldDefinition("funding_source", "Study funding source", FieldType.TEXT, required=False),
    ]


def get_case_report_schema() -> List[FieldDefinition]:
    """Schema for Case Reports/Series (e.g., for DPM systematic review)."""
    # Using LIST_TEXT (FlexibleList) for most fields to handle local model inconsistencies
    return [
        FieldDefinition("case_count", "Number of cases reported (integer)", FieldType.INTEGER, required=False),
        FieldDefinition("patient_age", "Patient age(s) in years", FieldType.LIST_TEXT, required=False),
        FieldDefinition("patient_sex", "Patient sex/gender", FieldType.LIST_TEXT, required=False),
        FieldDefinition("presenting_symptoms", "Initial presenting symptoms", FieldType.LIST_TEXT, required=False),
        FieldDefinition("diagnostic_method", "Method used for diagnosis", FieldType.LIST_TEXT, required=False),
        FieldDefinition("imaging_findings", "CT/X-ray/imaging findings", FieldType.LIST_TEXT, required=False),
        FieldDefinition("histopathology", "Histopathological findings", FieldType.LIST_TEXT, required=False),
        FieldDefinition("immunohistochemistry", "IHC markers/results", FieldType.LIST_TEXT, required=False),
        FieldDefinition("treatment", "Treatment provided", FieldType.LIST_TEXT, required=False),
        FieldDefinition("outcome", "Patient outcome/follow-up status", FieldType.LIST_TEXT, required=False),
        FieldDefinition("comorbidities", "Associated conditions/comorbidities", FieldType.LIST_TEXT, required=False),
    ]


def get_observational_schema() -> List[FieldDefinition]:
    """Schema for Observational Studies (cohort, case-control)."""
    return [
        FieldDefinition("study_design", "Type of observational study", FieldType.TEXT),
        FieldDefinition("sample_size", "Total number of participants", FieldType.INTEGER),
        FieldDefinition("setting", "Study setting (hospital, community, etc.)", FieldType.TEXT),
        FieldDefinition("exposure", "Main exposure/risk factor", FieldType.TEXT),
        FieldDefinition("outcome", "Main outcome measured", FieldType.TEXT),
        FieldDefinition("effect_estimate", "Effect estimate (OR, RR, HR, etc.)", FieldType.TEXT),
        FieldDefinition("confidence_interval", "95% CI for effect estimate", FieldType.TEXT),
        FieldDefinition("confounders_adjusted", "Confounders adjusted for", FieldType.TEXT, required=False),
        FieldDefinition("study_period", "Time period of study", FieldType.TEXT),
    ]


PREDEFINED_SCHEMAS = {
    "rct": get_rct_schema,
    "case_report": get_case_report_schema,
    "observational": get_observational_schema,
}


def interactive_schema_builder() -> List[FieldDefinition]:
    """
    Interactive CLI for building a custom extraction schema.
    
    Returns:
        List of FieldDefinition objects
    """
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    
    console = Console()
    fields = []
    
    console.print("\n[bold cyan]📋 Interactive Schema Builder[/bold cyan]")
    console.print("Define the variables you want to extract from each paper.\n")
    
    # Suggest predefined schemas
    console.print("[dim]Predefined schemas available: rct, case_report, observational[/dim]")
    use_predefined = Prompt.ask(
        "Use a predefined schema? (or 'custom')",
        choices=["rct", "case_report", "observational", "custom"],
        default="custom"
    )
    
    if use_predefined != "custom":
        return PREDEFINED_SCHEMAS[use_predefined]()
    
    # Custom schema building
    console.print("\n[bold]Enter your custom fields:[/bold]")
    console.print("[dim]Commands: 'undo' to remove last, 'delete <name>' to remove specific[/dim]")
    console.print("[dim]Press Enter with empty name to finish[/dim]\n")
    
    while True:
        name = Prompt.ask("Field name (e.g., 'sample_size')", default="")
        if not name:
            break
        
        # Handle Commands
        cmd = name.lower().strip()
        if cmd == "undo":
            if fields:
                removed = fields.pop()
                console.print(f"[yellow]↩ Undid last field: {removed.name}[/yellow]\n")
            else:
                console.print("[dim]Nothing to undo.[/dim]\n")
            continue
            
        if cmd.startswith("delete "):
            field_to_delete = cmd.replace("delete ", "").strip()
            initial_count = len(fields)
            fields = [f for f in fields if f.name != field_to_delete]
            if len(fields) < initial_count:
                console.print(f"[red]✗ Deleted field: {field_to_delete}[/red]\n")
            else:
                console.print(f"[dim]Field '{field_to_delete}' not found.[/dim]\n")
            continue

        # Sanitize name
        name = name.lower().replace(" ", "_").replace("-", "_")
        
        description = Prompt.ask(f"Description for '{name}'")
        
        field_type = Prompt.ask(
            "Data type",
            choices=["text", "integer", "float", "boolean", "list_text"],
            default="text"
        )
        
        required = Confirm.ask("Is this field required?", default=True)
        include_quote = Confirm.ask("Include source quote for traceability?", default=True)
        
        fields.append(FieldDefinition(
            name=name,
            description=description,
            field_type=FieldType(field_type),
            required=required,
            include_quote=include_quote,
        ))
        
        console.print(f"[green]✓ Added field: {name}[/green]\n")
    
    # Show summary
    if fields:
        table = Table(title="Extraction Schema")
        table.add_column("Field", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Required", style="yellow")
        table.add_column("Description")
        
        for f in fields:
            table.add_row(
                f.name,
                f.field_type.value,
                "Yes" if f.required else "No",
                f.description[:40] + "..." if len(f.description) > 40 else f.description
            )
        
        console.print(table)
    
    return fields


def infer_schema_from_csv(csv_path: str, header_line: int = 1) -> List[FieldDefinition]:
    """
    Infer extraction schema from a template CSV.
    
    Args:
        csv_path: Path to the CSV file
        header_line: 0-indexed line number containing headers (default 1 for 2nd line)
        
    Returns:
        List of FieldDefinition objects
    """
    # Read CSV, skipping metadata lines if needed
    try:
        df = pd.read_csv(csv_path, header=header_line)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        # Fallback to reading with default header if header_line fails or is wrong
        df = pd.read_csv(csv_path)

    fields = []
    
    for col in df.columns:
        # Clean column name
        raw_name = str(col).strip()
        if not raw_name or "Unnamed" in raw_name:
            continue
            
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_name.lower())
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        # Infer type from non-null values
        sample_values = df[col].dropna()
        
        field_type = FieldType.TEXT # Default
        
        if not sample_values.empty:
            # Check for boolean/integer flags (0/1)
            is_binary = sample_values.apply(lambda x: str(x).strip() in ['0', '1', '0.0', '1.0']).all()
            
            if is_binary:
                field_type = FieldType.INTEGER
            elif pd.api.types.is_numeric_dtype(sample_values):
                # Distinguish int vs float
                if all(sample_values % 1 == 0):
                    field_type = FieldType.INTEGER
                else:
                    field_type = FieldType.FLOAT
            else:
                # Check if it looks like a list
                # (Simple heuristic: contains commas or semicolons?)
                # For now, default to TEXT as our parsers handle coercing to string
                field_type = FieldType.TEXT

        # Determine if required (heuristic: if all rows have value)
        # However, for template CSVs, often they are empty or have sparse examples.
        # Safer to make everything optional unless specified otherwise.
        required = True 

        fields.append(FieldDefinition(
            name=clean_name,
            description=f"Extracted from column '{raw_name}'",
            field_type=field_type,
            required=required,
            include_quote=True # Default to True for traceability
        ))
        
    return fields


if __name__ == "__main__":
    # Demo: Build a case report schema
    schema = get_case_report_schema()
    Model = build_extraction_model(schema, "DPMExtractionModel")
    
    print(f"Created model: {Model.__name__}")
    print(f"Fields: {list(Model.model_fields.keys())}")
    
    # Show JSON schema
    import json
    print("\nJSON Schema:")
    print(json.dumps(Model.model_json_schema(), indent=2)[:1000])
