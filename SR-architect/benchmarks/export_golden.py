
import json
from pathlib import Path
from core.state_manager import StateManager

def export_golden():
    checkpoint_path = Path("benchmarks/golden_dataset/extraction_checkpoint.json")
    output_dir = Path("benchmarks/golden_dataset")
    
    manager = StateManager(checkpoint_path)
    state = manager.load()
    
    print(f"Exporting {len(state.results)} results from checkpoint...")
    
    for filename, data in state.results.items():
        with open(output_dir / f"{filename}.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"Exported {filename}")

if __name__ == "__main__":
    export_golden()
