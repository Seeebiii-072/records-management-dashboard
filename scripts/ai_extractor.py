"""
ai_extractor.py - Smart PDF Extraction
=======================================
PDF ke actual headings, sections aur context se
departments aur tools extract karta hai.
Koi hardcoded department names nahi.
"""

import re
import json
import urllib.request

OLLAMA_API   = "http://localhost:11434"
OLLAMA_MODEL = "qwen2:0.5b"

# ── KNOWN SYSTEMS ─────────────────────────────────────────────────────────────
KNOWN_SYSTEMS = [
    "LaserFiche", "Laserfiche", "NeoGov", "Synergy", "ONESolution",
    "SharePoint", "DocuWare", "OpenText", "FileNet", "Workday",
    "PeopleSoft", "Oracle", "Munis", "Tyler Technologies", "OnBase",
    "Documentum", "M-Files", "FileHold", "Alfresco", "Box",
    "PowerBI", "Power BI", "Tableau", "ArcGIS", "Accela",
    "Cityworks", "Questys", "SunGard", "PaperVision", "Hyland",
    "DocuSign", "iManage", "Perceptive", "Active Directory",
    "Microsoft Teams", "Google Drive", "Outlook", "SAP",
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


# ── RELATIONSHIP DETECT ───────────────────────────────────────────────────────
def detect_relationship(context):
    context_lower = context.lower()
    scores = {rel: 0 for rel in RELATIONSHIP_PATTERNS}
    for rel_type, patterns in RELATIONSHIP_PATTERNS.items():
        for p in patterns:
            if re.search(p, context_lower):
                scores[rel_type] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Workflow User"


# ── EXTRACT ALL DEPARTMENTS FROM PDF ─────────────────────────────────────────
def extract_all_departments(text):
    """
    PDF ke har heading, section title aur department mention ko nikalo.
    Sirf PDF content se — kuch bhi hardcoded nahi.
    """
    departments = []
    seen = set()
    lines = text.split('\n')

    # Department indicator words
    dept_words = [
        'department', 'dept', 'division', 'office', 'bureau',
        'services', 'affairs', 'management', 'operations', 'section',
        'unit', 'branch', 'team', 'group', 'administration', 'center',
        'authority', 'board', 'committee', 'agency', 'directorate',
        'ministry', 'school', 'college', 'faculty', 'institute',
        'finance', 'accounting', 'hr', 'legal', 'it', 'procurement',
        'payroll', 'audit', 'compliance', 'communications', 'planning',
        'operations', 'technology', 'infrastructure', 'security',
        'records', 'archives', 'library', 'research', 'development',
        'marketing', 'sales', 'support', 'customer', 'public',
        'human resources', 'information technology', 'general counsel',
    ]

    for i, line in enumerate(lines):
        s = line.strip()
        if not s or len(s) < 3 or len(s) > 100:
            continue

        s_lower = s.lower()

        # Check 1: Line has department indicator word
        has_dept_word = any(dw in s_lower for dw in dept_words)

        # Check 2: ALL CAPS heading
        is_caps = (s.isupper() and 3 < len(s) < 80 and
                   not s.startswith('•') and not s.startswith('-'))

        # Check 3: Numbered section heading
        is_numbered = bool(re.match(r'^\d+[\.\)]\s+[A-Z]', s)) and len(s) < 80

        # Check 4: Title Case (likely heading)
        words = s.split()
        is_title = (
            2 <= len(words) <= 8 and
            sum(1 for w in words if w and w[0].isupper()) >= len(words) * 0.6 and
            not s.endswith('.') and not s.endswith(',')
        )

        # Check 5: "X Department", "Department of X" pattern
        is_dept_pattern = bool(re.search(
            r'(department of|office of|division of|bureau of|'
            r'board of|committee of|section of|unit of|'
            r'\w+ department|\w+ division|\w+ office|\w+ services|'
            r'\w+ bureau|\w+ board|\w+ unit|\w+ section)',
            s_lower
        ))

        if (has_dept_word or is_caps or is_numbered or is_dept_pattern) and (is_title or is_caps or is_numbered or is_dept_pattern):
            # Clean the name
            clean = re.sub(r'^\d+[\.\)]\s*', '', s).strip()
            clean = re.sub(r'[:\-–—]+$', '', clean).strip()
            clean = re.sub(r'\s+', ' ', clean)

            # Skip if too short, too long, or looks like a sentence
            if (len(clean) < 3 or len(clean) > 80 or
                    clean.endswith('.') or
                    clean.lower() in ['the', 'and', 'or', 'for', 'in', 'of']):
                continue

            key = clean.lower().strip()
            if key not in seen:
                seen.add(key)
                departments.append(clean)

    return departments


# ── EXTRACT DEPT-TOOL PAIRS FROM CONTEXT ─────────────────────────────────────
def extract_from_sections(text):
    """
    PDF ko sections mein divide karo aur har section mein
    tools dhundo — section heading = department name.
    """
    results = []
    seen = set()
    lines = text.split('\n')

    current_heading = None
    current_content = []

    def process_section(heading, content):
        if not heading or not content:
            return []
        content_text = ' '.join(content)
        section_results = []

        for system in KNOWN_SYSTEMS:
            if system.lower() in content_text.lower():
                rel = detect_relationship(content_text)
                key = (heading.lower()[:30], system.lower())
                if key not in seen:
                    seen.add(key)
                    section_results.append({
                        "department": heading,
                        "tool": system,
                        "relationship": rel,
                        "usage": f"{heading} uses {system}",
                        "business_context": content_text[:400]
                    })
        return section_results

    for line in lines:
        s = line.strip()
        if not s:
            continue

        # Detect heading
        is_heading = (
            (s.isupper() and 3 < len(s) < 80) or
            bool(re.match(r'^\d+[\.\)]\s+[A-Z]', s)) or
            bool(re.search(r'(department|division|office|services|board|committee|unit|section|school|faculty)', s.lower())) and len(s) < 80
        )

        if is_heading:
            # Process previous section
            if current_heading:
                results.extend(process_section(current_heading, current_content))
            # Clean heading
            clean = re.sub(r'^\d+[\.\)]\s*', '', s).strip()
            clean = re.sub(r'[:\-–—]+$', '', clean).strip()
            current_heading = clean
            current_content = []
        else:
            current_content.append(s)

    # Last section
    if current_heading:
        results.extend(process_section(current_heading, current_content))

    return results


# ── CONTEXT-BASED EXTRACTION ──────────────────────────────────────────────────
def extract_from_context(text):
    """
    Har system ke aas paas ka context dekho aur
    nearest department mention dhundo.
    """
    results = []
    seen = set()
    text_lower = text.lower()

    # Common department patterns to find near systems
    dept_indicators = [
        r'([A-Z][a-zA-Z\s&/,]{2,50}(?:Department|Division|Office|Services|Board|Unit|Section|School|Bureau|Committee|Agency))',
        r'((?:Department|Division|Office|Bureau)\s+of\s+[A-Z][a-zA-Z\s]{2,40})',
        r'([A-Z][a-zA-Z\s]{2,30}(?:\s+Team|\s+Group|\s+Staff|\s+Personnel))',
    ]

    for system in KNOWN_SYSTEMS:
        pattern = re.escape(system.lower())
        matches = list(re.finditer(pattern, text_lower))

        for m in matches[:8]:
            start = max(0, m.start() - 500)
            end   = min(len(text), m.end() + 500)
            ctx   = text[start:end]

            # Find department in context
            dept = None
            for dp in dept_indicators:
                found = re.findall(dp, ctx)
                if found:
                    dept = found[0].strip()
                    dept = re.sub(r'\s+', ' ', dept)
                    if 3 < len(dept) < 80:
                        break

            if not dept:
                continue

            rel = detect_relationship(ctx)
            key = (dept.lower()[:30], system.lower())
            if key not in seen:
                seen.add(key)
                results.append({
                    "department": dept,
                    "tool": system,
                    "relationship": rel,
                    "usage": f"{dept} uses {system} — from PDF context",
                    "business_context": ctx.replace('\n', ' ')[:400]
                })

    return results


# ── LLM EXTRACTION ────────────────────────────────────────────────────────────
def llm_extract(text):
    """Ollama se extract karo agar available ho."""
    print("🤖 Trying Ollama LLM...")
    results = []

    chunk_size = 3000
    words = text.split()
    chunks = []
    cur = []
    count = 0
    for w in words:
        cur.append(w)
        count += len(w) + 1
        if count >= chunk_size:
            chunks.append(" ".join(cur))
            cur = []
            count = 0
    if cur:
        chunks.append(" ".join(cur))

    for i, chunk in enumerate(chunks[:10], 1):
        prompt = f"""Analyze this government records management document text.

Extract ALL departments/offices/divisions and their software systems.

Return ONLY a JSON array:
[{{"department": "exact name from text", "tool": "exact software name", "relationship": "System Owner OR Workflow User OR Records Officer OR Records Custodian", "usage": "one sentence", "business_context": "brief context"}}]

If nothing found return [].
Only real software systems. Use exact names from the document.

TEXT:
{chunk}

JSON:"""

        try:
            payload = json.dumps({
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1500}
            }).encode()

            req = urllib.request.Request(
                f"{OLLAMA_API}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = json.loads(resp.read()).get("response", "").strip()

            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                if isinstance(parsed, list) and len(parsed) > 0:
                    results.extend(parsed)
                    print(f"   Chunk {i}: LLM found {len(parsed)} records")

        except Exception as e:
            print(f"   Chunk {i} LLM error: {e}")
            continue

    print(f"   LLM total: {len(results)} records")
    return results


# ── MAIN HYBRID PIPELINE ──────────────────────────────────────────────────────
def hybrid_extract(text):
    """
    3-layer extraction:
    1. Section-based (headings → departments)
    2. Context-based (system → nearest dept)
    3. LLM (if Ollama running)
    All from PDF — nothing hardcoded.
    """
    print(f"\n{'='*50}")
    print("  PDF EXTRACTION PIPELINE")
    print(f"{'='*50}")
    print(f"   Text: {len(text):,} chars")

    all_results = []

    # Layer 1: Section-based
    print("\n📑 Layer 1: Section-based extraction...")
    sec_results = extract_from_sections(text)
    print(f"   Found: {len(sec_results)} records")
    all_results.extend(sec_results)

    # Layer 2: Context-based
    print("\n🔍 Layer 2: Context-based extraction...")
    ctx_results = extract_from_context(text)
    print(f"   Found: {len(ctx_results)} records")
    all_results.extend(ctx_results)

    # Layer 3: LLM (if available)
    try:
        req = urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=3)
        if req.status == 200:
            print("\n🤖 Layer 3: Ollama LLM extraction...")
            llm_results = llm_extract(text)
            all_results.extend(llm_results)
    except Exception:
        print("\n⚠️ Layer 3: Ollama not available — skipping")

    # Deduplicate
    seen  = set()
    final = []
    for item in all_results:
        dept = str(item.get("department", "")).strip()
        tool = str(item.get("tool", "")).strip()
        if not dept or not tool or len(dept) < 2:
            continue
        key = (dept.lower()[:30], tool.lower())
        if key not in seen:
            seen.add(key)
            final.append(item)

    print(f"\n✅ Total unique records: {len(final)}")
    return final
