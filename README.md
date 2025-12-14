# Research Projects Repository

A centralized hub for all research, data analysis, literature reviews, and manuscript writing using local LLMs (Ollama), cloud APIs (OpenRouter), and version control (GitHub).

---

## 📁 Projects

### 1. DPM Systematic Review
- **Status**: In Progress
- **Goal**: Systematic review and meta-analysis of diffuse pulmonary meningotheliomatosis
- **Location**: `DPM-systematic-review/`
- **Key Files**: 
  - Data extraction: `data/extracted_studies.csv`
  - Analysis: `analysis/meta_analysis.py`
  - Draft: `manuscript/`

### 2. ICU Quality Improvement
- **Status**: Planning
- **Goal**: QI project on ICU alarm fatigue and clinical decision support
- **Location**: `ICU-quality-improvement/`

### 3. AI Experiments
- **Status**: Ongoing
- **Goal**: Explore local LLMs for research workflows
- **Location**: `ai-experiments/`

---

## 📊 Folder Structure

Each project follows this standard organization:

```text
project-name/
├── papers/              # PDF articles, literature notes
│   └── *.pdf
├── data/                # CSV files, extracted datasets
│   ├── extracted_studies.csv
│   ├── effect_sizes.csv
│   └── outcomes.csv
├── analysis/            # Python scripts, Jupyter notebooks
│   ├── meta_analysis.py
│   ├── forest_plot.py
│   ├── analysis.ipynb
│   └── results/
├── manuscript/          # Draft sections, final writing
│   ├── abstract.md
│   ├── methods.md
│   ├── results.md
│   ├── discussion.md
│   └── references.md
└── README.md            # Project-specific notes
```

---

## 🛠️ Tools & Technologies

- **Local LLM Inference**: Ollama (mistral, deepseek-coder, qwen2.5)
- **Local LLM Interface**: Open WebUI (Docker)
- **Cloud LLM API**: OpenRouter (for larger models: 70B+)
- **Data Analysis**: Python (pandas, numpy, scipy)
- **Visualization**: matplotlib, seaborn
- **Version Control**: Git + GitHub
- **Writing**: Markdown

---

## 📝 Workflow

### 1. Literature Review & Data Extraction
Use Open WebUI (Ollama) to summarize abstracts, extract PICO elements, identify outcomes and effect sizes, and export as CSV.

### 2. Data Analysis
Use Python scripts to load CSV data, calculate summary statistics, generate forest plots, perform meta-analysis, and export results.

### 3. Manuscript Writing
Use LLM + manual editing to draft methods section, synthesize results, write discussion, and polish for submission.

### 4. Version Control
After each meaningful change: git add . → git commit -m "message" → git push

---

## 🔄 Git Workflow

### Making changes

git add .
git commit -m "Descriptive message of what changed"
git push

### Good commit messages
- ✅ "Add PICO extraction from papers 1-5"
- ✅ "Fix forest plot x-axis labels"
- ✅ "Draft results section from meta-analysis"

### Viewing history

git log
git show COMMIT_HASH
git checkout COMMIT_HASH -- filename

---

## 💾 Backup & Safety

- **Local**: All work on your Mac in ~/Projects/research-projects/
- **Cloud**: Mirrored to GitHub (automatic with git push)
- **Protection**: If your Mac breaks, clone from GitHub: git clone git@github.com:YOUR_USERNAME/research-projects.git

---

## 🤖 Using Ollama + Open WebUI for Data Extraction

### Starting Ollama & Open WebUI

Terminal 1: ollama serve
Terminal 2: open-webui serve
Then go to http://localhost:8080

### Example extraction workflow
1. Open WebUI → New chat
2. Select model: Qwen 2.5-7B
3. Paste prompt with abstract
4. Copy output → Paste into data/extracted_studies.csv
5. Commit: git commit -m "Add paper X extraction"

---

## 📚 Models & Use Cases

Quick summaries: Qwen 2.5-3B (local) or DeepSeek-V3-7B on OpenRouter
Data extraction (PICO): Qwen 2.5-7B (local) or Qwen 3-14B on OpenRouter
Literature synthesis: Qwen 2.5-14B (local) or DeepSeek-V3-70B on OpenRouter
Code generation: DeepSeek-Coder-15B (local)
Manuscript polish: Qwen 2.5-14B (local) or GPT-4o / Claude on OpenRouter

---

## 🚀 Getting Started

After each change: git add . → git commit -m "message" → git push

---

## 💡 Tips

- Commit often: After finishing extraction from 3-5 papers
- Write clear messages: Future you will thank present you
- Use descriptive filenames: meta_analysis.py not script.py
- Test code locally: Before committing
- Keep PDFs organized: Use paper name or ID in filename

---

Last updated: December 13, 2025
