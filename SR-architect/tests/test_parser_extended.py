import pytest
import os
from unittest.mock import MagicMock, patch, mock_open
from core.parser import DocumentParser, ParsedDocument

@pytest.fixture
def parser():
    return DocumentParser()

def test_parse_text(parser, tmp_path):
    # Create dummy text file
    f = tmp_path / "test.txt"
    f.write_text("Paragraph 1.\n\nParagraph 2.")
    
    doc = parser.parse_text(str(f))
    # _simple_chunk combines text if < 1000 chars, so expected to be 1 chunk
    assert len(doc.chunks) == 1
    assert "Paragraph 1" in doc.chunks[0].text
    assert "Paragraph 2" in doc.chunks[0].text

def test_parse_markdown(parser, tmp_path):
    # Create dummy md file
    f = tmp_path / "test.md"
    f.write_text("# Intro\nHello world.\n\n## Methods\nWe did things.")
    
    doc = parser.parse_markdown(str(f))
    
    # Expect: Intro chunk, Methods chunk
    # The logic keeps previous chunk when hitting new header
    # 1. Intro -> "Hello world."
    # 2. Methods -> "We did things."
    
    assert len(doc.chunks) == 2
    assert doc.chunks[0].section == "Intro"
    assert "Hello world" in doc.chunks[0].text
    assert doc.chunks[1].section == "Intro" # logic check: does subsection change update section?
    # Wait, looking at code:
    # if line.startswith('# '): current_section = line[2:] 
    # if line.startswith('## '): current_subsection = line[3:]
    # So chunk 1 is Intro. 
    # Chunk 2 comes after '## Methods'. 
    # Ah, implementation details:
    # When hitting '## Methods', we save the PREVIOUS text (from Intro).
    # Then we set current_subsection. 
    # Then we read "We did things."
    # Then end of loop saves "We did things." with section="Intro" and subsection="Methods".
    
    assert doc.chunks[1].subsection == "Methods"
    assert "We did things" in doc.chunks[1].text

def test_parse_html(parser, tmp_path):
    # Mock BS4 to avoid dependency in test env if missing
    with patch("core.parser.BeautifulSoup") as MockBS:
        # Construct a mock soup tree
        mock_soup = MagicMock()
        
        # Elements
        h1 = MagicMock()
        h1.name = "h1"
        h1.get_text.return_value = "Title"
        
        p1 = MagicMock()
        p1.name = "p"
        p1.get_text.return_value = "Content 1"
        
        h2 = MagicMock()
        h2.name = "h2"
        h2.get_text.return_value = "Section 2"
        
        p2 = MagicMock()
        p2.name = "p"
        p2.get_text.return_value = "Content 2"
        
        mock_soup.find_all.return_value = [h1, p1, h2, p2]
        MockBS.return_value = mock_soup
        
        # Create dummy file to allow open() to work
        f = tmp_path / "test.html"
        f.touch()
        
        doc = parser.parse_html(str(f))
        
        assert len(doc.chunks) == 2
        assert doc.chunks[0].section == "Title"
        assert doc.chunks[0].text == "Content 1"
        assert doc.chunks[1].section == "Section 2"
        assert doc.chunks[1].text == "Content 2"

def test_parse_file_dispatch(parser, tmp_path):
    # Test dispatch logic
    txt = tmp_path / "test.txt"
    txt.touch()
    
    with patch.object(parser, 'parse_text') as mock_txt:
        parser.parse_file(str(txt))
        mock_txt.assert_called_once()
        
    md = tmp_path / "test.md"
    md.touch()
    with patch.object(parser, 'parse_markdown') as mock_md:
        parser.parse_file(str(md))
        mock_md.assert_called_once()

def test_parse_folder(parser, tmp_path):
    # Create mix of files
    (tmp_path / "a.txt").touch()
    (tmp_path / "b.html").touch()
    (tmp_path / "c.pdf").touch() # Should try to parse
    
    # Mock specific parsers to avoid actual errors/returns
    with patch.object(parser, 'parse_file') as mock_parse:
        parser.parse_folder(str(tmp_path))
        assert mock_parse.call_count == 3
