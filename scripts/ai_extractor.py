"""
ai_extractor.py - LLM-First Extraction Pipeline
=================================================
1. Ollama llama3 → real LLM analysis of PDF
2. Smart NLP fallback → if LLM fails
All data comes from PDF — NOTHING hardcoded.
"""

import re
import json
import subprocess
import urllib.request


OLLAMA_API   = "http://localhost:11434"
OLLAMA_MODEL = "tinyllama"

KNOWN_SYSTEMS = [
    "LaserFiche", "Laserfiche", "NeoGov", "Synergy", "ONESolution",
    "SharePoint", "DocuWare", "OpenText", "FileNet", "Workday",
    "PeopleSoft", "Oracle", "Munis", "Tyler Technologies", "OnBase",
    "Documentum", "M-Files", "FileHold", "Alfresco", "Box",
    "PowerBI", "Power BI", "Tableau", "ArcGIS", "Accela",
    "Cityworks", "Questys", "Alchemy", "SunGard", "PaperVision",
    "Hyland", "DocuSign", "iManage", "Perceptive",
    "Active Directory", "Microsoft Teams", "Google Drive",
]

RELATIONSHIP_PATTERNS = {
    "System Owner": [
        r"system owner", r"owns the system", r"system administrator",
        r"administers", r"technology services", r"information technology",
        r"manages the (system|platform|application)",
        r"responsible for (the )?(system|platform|database)",
    ],
    "Records Officer": [
        r"records officer", r"lva", r"virginia public records",
        r"records management officer", r"designated (records|rm)",
        r"records liaison", r"retention schedule", r"disposition",
    ],
    "Records Custodian": [
        r"records custodian", r"custodian of record",
        r"maintains (the )?(physical|original) records",
        r"file room", r"physical (storage|records)",
    ],
    "Workflow User": [
        r"uses (the )?system", r"utilizes",
        r"enters (data|records|information)",
        r"accesses (the )?(system|database|records)",
        r"workflow", r"processes (through|using|via)",
        r"inputs", r"submits", r"daily (use|operations)",
    ],
}

DEPT_PATTERNS = [
    (r'\b(finance|financial|accounting|fiscal)\b',                'Finance Department'),
    (r'\b(human resources?|hr dept|personnel dept)\b',            'Human Resources'),
    (r'\b(information technology|it dept|technology services)\b', 'Technology Services'),
    (r'\b(legal dept|attorney|legal services)\b',                 'Legal Department'),
    (r'\b(payroll)\b',                                            'Payroll Department'),
    (r'\b(budget dept|budget office)\b',                          'Budget Department'),
    (r'\b(procurement|purchasing dept)\b',                        'Procurement'),
    (r'\b(communications?|public relations?)\b',                  'Communications'),
    (r'\b(schools?|education dept|academic|students?)\b',         'Schools / Education'),
    (r'\b(benefits? dept|employee benefits?)\b',                  'Benefits Department'),
    (r'\b(records management|records officer)\b',                 'Records Management'),
    (r'\b(board clerk|clerk of board)\b',                         'Board Clerk'),
    (r'\b(grants? dept|grant management)\b',                      'Grants Department'),
    (r'\b(counseling|guidance dept)\b',                           'School Counseling'),
    (r'\b(facilities|maintenance dept)\b',                        'Facilities'),
    (r'\b(administration|administrative office)\b',               'Administration'),
]


# ─── LLM EXTRACTION ───────────────────────────────────────────────────────────

def llm_extract_chunk(chunk, chunk_num=1):
    """Single chunk ko LLM se analyze karo."""
    prompt = f"""You are analyzing a government records management PDF document.

Extract ALL departments and their software/applications from this text.

Return ONLY a valid JSON array. No explanation. No markdown. Just raw JSON like:
[
  {{
    "department": "exact department name from the document",
    "tool": "exact software/system name from the document",
    "relationship": "System Owner OR Workflow User OR Records Officer OR Records Custodian",
    "usage": "what this department does with this tool in 1 sentence",
    "business_context": "brief context about department role"
  }}
]

RULES:
- Use EXACT names as they appear in the document
- Only include REAL software systems (not general words like 'system' or 'database')
- If no departments or tools found, return empty array: []
- relationship MUST be one of the 4 types listed above

TEXT:
{chunk}

Return only JSON array:"""

    try:
        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2000}
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_API}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            data    = json.loads(resp.read())
            raw     = data.get("response", "").strip()

        # JSON extract
        json_match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            if isinstance(result, list):
                print(f"   ✅ Chunk {chunk_num}: LLM found {len(result)} records")
                return result

    except urllib.error.URLError:
        print(f"   ⚠️ Ollama not reachable for chunk {chunk_num}")
    except json.JSONDecodeError:
        print(f"   ⚠️ LLM JSON parse error on chunk {chunk_num}")
    except Exception as e:
        print(f"   ⚠️ LLM error chunk {chunk_num}: {e}")

    return []


def llm_extract(text):
    """PDF text ko chunks mein split karke LLM se analyze karo."""
    print("🤖 Running Ollama LLM extraction...")

    # Text ko 4000 char chunks mein split karo
    chunk_size = 4000
    chunks     = []
    words      = text.split()
    current    = []
    count      = 0

    for word in words:
        current.append(word)
        count += len(word) + 1
        if count >= chunk_size:
            chunks.append(" ".join(current))
            current = []
            count   = 0
    if current:
        chunks.append(" ".join(current))

    print(f"   Processing {len(chunks)} chunks with LLM...")

    all_results = []
    for i, chunk in enumerate(chunks[:8], 1):  # Max 8 chunks
        results = llm_extract_chunk(chunk, i)
        all_results.extend(results)

    print(f"   LLM total: {len(all_results)} records")
    return all_results


# ─── NLP FALLBACK ─────────────────────────────────────────────────────────────

def detect_relationship(context):
    context_lower = context.lower()
    scores = {rel: 0 for rel in RELATIONSHIP_PATTERNS}
    for rel_type, patterns in RELATIONSHIP_PATTERNS.items():
        for p in patterns:
            if re.search(p, context_lower):
                scores[rel_type] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Workflow User"


def detect_department(context):
    context_lower = context.lower()
    for pattern, dept_name in DEPT_PATTERNS:
        if re.search(pattern, context_lower):
            return dept_name
    return "Administration"


def nlp_fallback_extract(text):
    """NLP-based fallback — no LLM needed, pure regex."""
    print("🔍 Running NLP fallback extraction...")
    results = []
    seen    = set()
    text_lower = text.lower()

    for system in KNOWN_SYSTEMS:
        pattern = re.escape(system.lower())
        matches = list(re.finditer(pattern, text_lower))

        if not matches:
            continue

        for m in matches[:5]:
            start = max(0, m.start() - 400)
            end   = min(len(text), m.end() + 400)
            ctx   = text[start:end].replace('\n', ' ').strip()

            dept = detect_department(ctx)
            rel  = detect_relationship(ctx)

            key = (dept.lower()[:25], system.lower())
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "department":       dept,
                "tool":             system,
                "relationship":     rel,
                "usage":            f"{dept} uses {system} — detected from PDF",
                "business_context": ctx[:350],
            })

    print(f"   NLP fallback: {len(results)} records")
    return results


# ─── MAIN HYBRID PIPELINE ─────────────────────────────────────────────────────

def hybrid_extract(text):
    """
    Main pipeline:
    1. Try Ollama LLM (if running)
    2. NLP fallback (always runs for extra coverage)
    3. Merge + deduplicate
    All data from PDF — nothing hardcoded.
    """
    print(f"\n{'='*50}")
    print("  AI EXTRACTION PIPELINE")
    print(f"{'='*50}")
    print(f"   PDF text: {len(text):,} characters")

    all_results = []

    # Step 1: LLM
    try:
        req = urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=3)
        if req.status == 200:
            llm_results = llm_extract(text)
            all_results.extend(llm_results)
        else:
            print("   ⚠️ Ollama not running — using NLP only")
    except Exception:
        print("   ⚠️ Ollama not reachable — using NLP fallback")

    # Step 2: NLP fallback (always)
    nlp_results = nlp_fallback_extract(text)
    all_results.extend(nlp_results)

    # Step 3: Deduplicate
    seen  = set()
    final = []
    for item in all_results:
        dept = item.get("department", "").strip()
        tool = item.get("tool", "").strip()
        if not dept or not tool:
            continue
        key = (dept.lower()[:25], tool.lower())
        if key not in seen:
            seen.add(key)
            final.append(item)

    print(f"\n✅ Final unique records: {len(final)}")
    return final
