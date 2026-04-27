# 🧠 Records Management AI Dashboard

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run app
streamlit run app.py
```

## Ollama Auto-Setup
- Open the sidebar → Click **"Auto-Setup Ollama"**
- App will automatically download + install Ollama + pull llama3
- First run: ~5-10 mins (downloads 4GB model)
- After that: 100% offline, instant analysis

## How It Works
1. Upload PDFs → app extracts text
2. Ollama llama3 reads PDF chunks → finds departments + tools
3. NLP fallback runs in parallel for extra coverage  
4. Results shown in dashboard: table, charts, network graph
5. Export as Excel or CSV
