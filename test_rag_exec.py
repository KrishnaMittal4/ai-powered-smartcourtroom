import pypdf
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Step 1: Ingestion
pdf_path = "judgments/case1_cheque_bounce.pdf"
reader = pypdf.PdfReader(pdf_path)
full_text = reader.pages[0].extract_text()

# Step 2: Chunking by numbered paragraphs
raw_chunks = re.split(r'\n(?=\d+\.\s)', full_text)
chunks = [c.strip() for c in raw_chunks if c.strip()]
print(f"[RAG INGESTION] Indexed {len(chunks)} chunks from {pdf_path}")

# Step 3: Retrieval
query = "What is the statutory presumption under Section 139 and how can it be rebutted?"
query_terms = set(re.findall(r'\w+', query.lower()))

scored = []
for idx, ch in enumerate(chunks):
    score = len(query_terms.intersection(set(re.findall(r'\w+', ch.lower()))))
    scored.append((score, idx, ch))

scored.sort(key=lambda x: x[0], reverse=True)
top_score, top_idx, top_chunk = scored[0]

print(f"\n[RAG RETRIEVAL] Best Matching Chunk #{top_idx+1} (Relevance Score: {top_score}):")
print(f"\"{top_chunk.replace(chr(10), ' ')[:280]}...\"")

# Step 4: Grounded Generation via Groq
import groq
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

prompt = f"""You are a Legal RAG assistant. Answer the user query using ONLY the provided case passage below.

Retrieved Case Passage:
\"\"\"{top_chunk}\"\"\"

Question: {query}

Provide a structured legal answer citing the specific paragraph.
"""

resp = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": prompt}]
)

print("\n[RAG GENERATED & GROUNDED ANSWER]")
print(resp.choices[0].message.content)
