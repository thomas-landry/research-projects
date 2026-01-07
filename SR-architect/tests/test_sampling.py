
import pytest
from pathlib import Path
import os
import shutil
from agents.schema_discovery import SchemaDiscoveryAgent

@pytest.fixture
def mock_papers_dir(tmp_path):
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    
    # Create some dummy PDFs
    for i in range(10):
        paper = papers_dir / f"paper_{i}.pdf"
        paper.write_text("dummy content " * 100) # Small but non-empty
        
    # Create a very small file (e.g., corrupted or placeholder)
    small_paper = papers_dir / "tiny.pdf"
    small_paper.write_text("too small")
    
    # Create a non-PDF
    readme = papers_dir / "README.md"
    readme.write_text("not a pdf")
    
    return papers_dir

def test_get_sample_papers(mock_papers_dir):
    agent = SchemaDiscoveryAgent()
    
    # We need to implement or expose the sampling logic
    # For now, let's assume we add a method 'get_sample_papers'
    if hasattr(agent, "get_sample_papers"):
        sample = agent.get_sample_papers(str(mock_papers_dir), sample_size=3)
        
        assert len(sample) == 3
        assert all(p.endswith(".pdf") for p in sample)
        assert "tiny.pdf" not in [os.path.basename(p) for p in sample], "Should skip tiny files"
    else:
        # If not implemented, the test fails to remind us to implement it as per task
        pytest.fail("SchemaDiscoveryAgent missing 'get_sample_papers' method")

def test_sampling_randomness(mock_papers_dir):
    agent = SchemaDiscoveryAgent()
    
    if hasattr(agent, "get_sample_papers"):
        sample1 = agent.get_sample_papers(str(mock_papers_dir), sample_size=5, seed=42)
        sample2 = agent.get_sample_papers(str(mock_papers_dir), sample_size=5, seed=43)
        
        # With enough files, different seeds should likely produce different samples
        assert sample1 != sample2
    else:
        pytest.skip("get_sample_papers not implemented")
