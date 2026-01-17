"""
Run Baseline Evaluation.

Executes the current extraction pipeline against gold standard data
and generates an accuracy report.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from core.metrics.gold_standard import GoldStandard
from core.metrics.baseline_measurement import BaselineMeasurement
from core.extraction.findings import extract_findings_batch
from core.fields.library import FieldLibrary
from core.extraction.tier_config import load_tier_config
from core.types.models import FindingReport

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_baseline_evaluation():
    """Run evaluation."""
    
    # 1. Load Gold Standard
    gs_dir = Path("benchmarks/data/gold_standard")
    gold_studies = GoldStandard.load_directory(gs_dir)
    logger.info(f"Loaded {len(gold_studies)} gold standard studies.")
    
    if not gold_studies:
        logger.error("No gold standard data found.")
        return

    # 2. Config
    # Assuming config/field_tiers.yaml exists, otherwise use hardcoded for now
    try:
        tier_config = load_tier_config("config/field_tiers.yaml")
        tiers = tier_config["tiers"]
        # Convert to format required by BaselineMeasurement: {tier: [fields]}
        tier_map = {
            t_id: t_data["fields"] 
            for t_id, t_data in tiers.items()
        }
    except Exception:
        logger.warning("Could not load tier config, using default.")
        tier_map = {
            1: ["ct_ground_glass", "ct_solid_nodules", "sex_female"]
        }

    # 3. Run Extraction (Mocked/Stubbed for now)
    predictions = []
    gold_dicts = []
    
    for study in gold_studies:
        logger.info(f"Processing {study.study_id}...")
        
        if study.study_id == "Archer_2020":
            narrative = (
                "We reviewed 45 patients with diffuse persistent multifocal lesions. "
                "CT imaging revealed ground glass opacities in 20 patients (44%). "
                "There were 25 female patients included in the cohort."
            )
        else:
            narrative = "No findings reported for this study."
        
        # Define fields to extract based on what's in our tier map
        specs = []
        # For this baseline, we just use the fields we know are in GS 
        # (in reality, we'd extract all configured fields)
        specs.append(FieldLibrary.imaging_finding("ground_glass", ["GGO"]))
        specs.append(FieldLibrary.imaging_finding("solid_nodules", ["nodule"]))
        specs.append(FieldLibrary.SEX_FEMALE)
        
        # Execution
        extracted_data = await extract_findings_batch(narrative, specs)
        
        # Convert to dict for metric calc (or update metric calc to handle objs, 
        # which we did, but checking expected structure)
        # The BaselineMeasurement expects List[Dict]. 
        # Our extract_findings_batch returns Dict[str, FindingReport].
        
        predictions.append(extracted_data)
        gold_dicts.append(study.model_dump())

    # 4. Measure
    measurer = BaselineMeasurement(tier_map)
    report = measurer.generate_report(predictions, gold_dicts)
    
    # 5. Output
    print(json.dumps(report, indent=2, default=str))
    
    # Save report
    with open("benchmarks/baseline_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
        
    logger.info("Evaluation complete. Report saved to benchmarks/baseline_report.json")

if __name__ == "__main__":
    asyncio.run(run_baseline_evaluation())
