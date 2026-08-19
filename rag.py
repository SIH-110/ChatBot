import os
import re
import warnings

# Reduce unnecessary warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from langchain_community.embeddings import HuggingFaceEmbeddings
import chromadb


# ============================================================
# CONFIGURATION
# ============================================================

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "doj_knowledge"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# Number of chunks initially retrieved from Chroma
INITIAL_K = 8

# Maximum number of chunks actually sent to the LLM
MAX_CONTEXT_CHUNKS = 4

# Maximum generated tokens
MAX_NEW_TOKENS = 180


# ============================================================
# DISPLAY
# ============================================================

print()
print("=" * 70)
print("                 DOJ / eCOURTS RAG CHATBOT")
print("=" * 70)
print()


# ============================================================
# DEVICE
# ============================================================

device = "cuda" if torch.cuda.is_available() else "cpu"

print("[1] Loading embedding model...")
print(f"Device: {device}")

if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

print()


# ============================================================
# EMBEDDING MODEL
# ============================================================

embedding_model_kwargs = {
    "device": device
}

encode_kwargs = {
    "normalize_embeddings": True
}

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs=embedding_model_kwargs,
    encode_kwargs=encode_kwargs
)

print("Embedding model loaded.")
print()


# ============================================================
# CHROMA
# ============================================================

print("[2] Loading Chroma database...")

client = chromadb.PersistentClient(
    path=CHROMA_DIR
)

try:
    collection = client.get_collection(
        name=COLLECTION_NAME
    )
except Exception as e:
    print()
    print("ERROR: Could not load Chroma collection.")
    print(f"Details: {e}")
    print()
    print("Make sure you have run:")
    print("    python ingest.py")
    raise SystemExit(1)

print("Chroma database loaded.")
print(f"Collection: {COLLECTION_NAME}")
print()


# ============================================================
# LANGUAGE MODEL
# ============================================================

print("[3] Loading local language model...")
print(f"Model: {LLM_MODEL}")

tokenizer = AutoTokenizer.from_pretrained(
    LLM_MODEL
)

if device == "cuda":
    model = AutoModelForCausalLM.from_pretrained(
        LLM_MODEL,
        torch_dtype=torch.float16
    )
else:
    model = AutoModelForCausalLM.from_pretrained(
        LLM_MODEL
    )

model.to(device)
model.eval()

print("Language model loaded.")
print()
print("Type 'exit' or 'quit' to stop.")
print()


# ============================================================
# DOMAIN KEYWORDS
# ============================================================

DOMAIN_KEYWORDS = {
    "ecourts": [
        "ecourts",
        "e-courts",
        "e courts",
        "court services",
        "cause list",
        "case status",
        "orders",
        "judgments",
        "judgement",
        "efiling",
        "e-filing",
        "epay",
        "e-pay",
        "virtual court",
        "justice clock",
        "high court",
        "district court"
    ],

    "njdg": [
        "njdg",
        "national judicial data grid",
        "pendency",
        "pending cases",
        "disposed cases",
        "judicial data grid"
    ],

    "echallan": [
        "echallan",
        "e-challan",
        "challan",
        "traffic challan",
        "traffic notice",
        "traffic enforcement"
    ],

    "fast_track": [
        "fast track",
        "fast-track",
        "fast track court",
        "fast track courts",
        "court functional",
        "cases disposed",
        "cases pending"
    ],

    "live_streaming": [
        "live streaming",
        "court live streaming",
        "live stream"
    ]
}


# ============================================================
# QUESTION NORMALIZATION
# ============================================================

def normalize(text):
    """
    Normalize text for keyword matching.
    """

    text = text.lower()

    # Replace punctuation with spaces
    text = re.sub(r"[^a-z0-9\s-]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# DETERMINE QUESTION DOMAIN
# ============================================================

def detect_domain(question):
    """
    Determine which major knowledge-base domain the question belongs to.

    Returns:
        domain name or None
    """

    q = normalize(question)

    scores = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            keyword_normalized = normalize(keyword)

            if keyword_normalized in q:
                # Exact domain keyword gets strong weight
                score += 3

        scores[domain] = score

    best_domain = max(
        scores,
        key=scores.get
    )

    if scores[best_domain] == 0:
        return None

    return best_domain


# ============================================================
# CHUNK DOMAIN CHECK
# ============================================================

def chunk_matches_domain(text, domain):
    """
    Check whether a retrieved chunk belongs to the requested domain.
    """

    if domain is None:
        return True

    text_normalized = normalize(text)

    keywords = DOMAIN_KEYWORDS.get(
        domain,
        []
    )

    for keyword in keywords:

        keyword_normalized = normalize(keyword)

        if keyword_normalized in text_normalized:
            return True

    return False


# ============================================================
# IMPORTANT TERM EXTRACTION
# ============================================================

def extract_question_terms(question):
    """
    Extract useful words from a question.

    This is deliberately simple because we want conservative
    retrieval rather than aggressive guessing.
    """

    stopwords = {
        "what",
        "is",
        "are",
        "the",
        "a",
        "an",
        "of",
        "for",
        "to",
        "in",
        "on",
        "and",
        "or",
        "does",
        "do",
        "how",
        "can",
        "where",
        "when",
        "which",
        "who",
        "why",
        "with",
        "by",
        "from",
        "under",
        "about",
        "tell",
        "me",
        "please",
        "provide",
        "give"
    }

    words = normalize(question).split()

    useful = []

    for word in words:

        if len(word) < 3:
            continue

        if word in stopwords:
            continue

        useful.append(word)

    return useful


# ============================================================
# KEYWORD EVIDENCE
# ============================================================

def keyword_evidence(question, document):
    """
    Calculate how much lexical evidence exists between
    the question and retrieved document.
    """

    q_terms = extract_question_terms(question)

    if not q_terms:
        return 0

    document_normalized = normalize(document)

    matches = 0

    for term in q_terms:

        if term in document_normalized:
            matches += 1

    return matches


# ============================================================
# SPECIAL DOMAIN EVIDENCE
# ============================================================

def strong_domain_evidence(question, document, domain):
    """
    Determine whether the document strongly supports the
    domain explicitly mentioned by the user.
    """

    if domain is None:
        return True

    q = normalize(question)
    d = normalize(document)

    keywords = DOMAIN_KEYWORDS.get(
        domain,
        []
    )

    # If the question explicitly names a domain,
    # the retrieved chunk should contain that domain
    # or one of its very strong associated terms.
    explicit_matches = 0

    for keyword in keywords:

        keyword_normalized = normalize(keyword)

        if keyword_normalized in q:

            if keyword_normalized in d:
                explicit_matches += 1

    return explicit_matches > 0


# ============================================================
# RETRIEVE DOCUMENTS
# ============================================================

def retrieve_documents(question):
    """
    Retrieve documents from Chroma and apply conservative
    filtering before sending anything to the LLM.
    """

    print()
    print("Retrieving relevant information...")

    query_embedding = embeddings.embed_query(
        question
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=INITIAL_K,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    print(
        f"Chroma initially returned {len(documents)} chunks."
    )

    domain = detect_domain(question)

    if domain:
        print(f"Detected question domain: {domain}")

    filtered = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        source = (
            metadata.get("source", "unknown")
            if metadata
            else "unknown"
        )

        print(
            f"  {source} | Distance: {distance:.4f}"
        )

        # ----------------------------------------------------
        # DOMAIN FILTER
        # ----------------------------------------------------

        if domain:

            if not chunk_matches_domain(
                document,
                domain
            ):

                print(
                    "    -> rejected: domain mismatch"
                )

                continue

        # ----------------------------------------------------
        # QUESTION TERM EVIDENCE
        # ----------------------------------------------------

        evidence = keyword_evidence(
            question,
            document
        )

        # If question has meaningful terms but
        # absolutely none appear in the chunk,
        # don't blindly trust the embedding.
        terms = extract_question_terms(question)

        if len(terms) >= 2 and evidence == 0:

            # Exception:
            # If the domain itself strongly appears,
            # allow it.
            if not strong_domain_evidence(
                question,
                document,
                domain
            ):

                print(
                    "    -> rejected: insufficient keyword evidence"
                )

                continue

        # ----------------------------------------------------
        # DISTANCE FILTER
        # ----------------------------------------------------

        # With normalized MiniLM embeddings,
        # smaller distance is better.
        #
        # We use a fairly generous threshold because
        # legal/document terminology can be semantically
        # different from the user's wording.

        if distance > 1.80:

            print(
                "    -> rejected: distance too large"
            )

            continue

        filtered.append(
            {
                "document": document,
                "metadata": metadata or {},
                "distance": distance,
                "evidence": evidence
            }
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    filtered.sort(
        key=lambda x: (
            x["distance"],
            -x["evidence"]
        )
    )

    # --------------------------------------------------------
    # REMOVE DUPLICATE DOCUMENTS
    # --------------------------------------------------------

    unique = []

    seen = set()

    for item in filtered:

        text = item["document"].strip()

        if text in seen:
            continue

        seen.add(text)

        unique.append(item)

    filtered = unique[
        :MAX_CONTEXT_CHUNKS
    ]

    print()
    print(
        f"After filtering: {len(filtered)} usable chunks."
    )

    return filtered


# ============================================================
# BUILD CONTEXT
# ============================================================

def build_context(results):
    """
    Build clean context for the language model.
    """

    context_parts = []

    for index, item in enumerate(results, start=1):

        source = item["metadata"].get(
            "source",
            "unknown"
        )

        document = item["document"].strip()

        context_parts.append(
            f"SOURCE {index}: {source}\n"
            f"{document}"
        )

    return "\n\n".join(
        context_parts
    )


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_answer(question, results):
    """
    Generate an answer strictly from retrieved context.
    """

    if not results:

        return (
            "I could not find sufficient information "
            "about this in the DOJ knowledge base."
        )

    context = build_context(
        results
    )

    prompt = f"""
You are a factual DOJ/eCourts knowledge-base assistant.

IMPORTANT RULES:

1. Answer ONLY using the information in the SOURCE TEXT.
2. Do NOT use your own general knowledge.
3. Do NOT invent facts.
4. Do NOT guess.
5. Do NOT provide information that is absent from the sources.
6. If the source text does not contain enough information to answer the question, say:
   "I could not find sufficient information about this in the DOJ knowledge base."
7. Do not mention information from unrelated source files.
8. Keep the answer concise and direct.
9. Do not repeat the same sentence.
10. Do not add legal advice.
11. Do not invent laws, punishments, dates, statistics, websites, or contact details.
12. If the question asks for a definition, give the definition found in the source.
13. If the question asks for a list, give only items supported by the source.
14. Do not say that something is true merely because it sounds plausible.
15. Do not mention the prompt or these instructions.

QUESTION:
{question}

SOURCE TEXT:
{context}

ANSWER:
"""

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=4096
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        output = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            repetition_penalty=1.10,
            pad_token_id=tokenizer.eos_token_id
        )

    generated_tokens = output[
        0
    ][
        inputs["input_ids"].shape[1]:
    ]

    answer = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    ).strip()

    # --------------------------------------------------------
    # CLEAN ANSWER
    # --------------------------------------------------------

    if not answer:

        return (
            "I could not find sufficient information "
            "about this in the DOJ knowledge base."
        )

    # Remove accidental source section generation
    answer = re.split(
        r"\n\s*(?:SOURCE|SOURCES|SOURCE FILE|SOURCE FILES)\s*:",
        answer,
        flags=re.IGNORECASE
    )[0].strip()

    # Remove common hallucinated endings
    answer = re.split(
        r"\n\s*Note\s*:",
        answer,
        flags=re.IGNORECASE
    )[0].strip()

    # Prevent excessively long answers
    sentences = re.split(
        r"(?<=[.!?])\s+",
        answer
    )

    cleaned_sentences = []

    seen_sentences = set()

    for sentence in sentences:

        normalized_sentence = normalize(
            sentence
        )

        if not normalized_sentence:
            continue

        if normalized_sentence in seen_sentences:
            continue

        seen_sentences.add(
            normalized_sentence
        )

        cleaned_sentences.append(
            sentence
        )

        if len(cleaned_sentences) >= 8:
            break

    answer = " ".join(
        cleaned_sentences
    ).strip()

    return answer


# ============================================================
# PRINT SOURCES
# ============================================================

def print_sources(results):
    """
    Print unique source filenames.
    """

    if not results:
        return

    sources = []

    for item in results:

        source = item["metadata"].get(
            "source",
            "unknown"
        )

        if source not in sources:
            sources.append(source)

    print()
    print("Sources retrieved:")

    for source in sources:

        matching = [
            item
            for item in results
            if item["metadata"].get(
                "source",
                "unknown"
            ) == source
        ]

        best_distance = min(
            item["distance"]
            for item in matching
        )

        print(
            f"  - {source} "
            f"(distance: {best_distance:.4f})"
        )


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:

        question = input(
            "You: "
        ).strip()

    except (
        KeyboardInterrupt,
        EOFError
    ):

        print()
        print("Goodbye!")
        break

    if not question:
        continue

    if question.lower() in {
        "exit",
        "quit"
    }:

        print()
        print("Goodbye!")
        break

    # --------------------------------------------------------
    # RETRIEVE
    # --------------------------------------------------------

    results = retrieve_documents(
        question
    )

    # --------------------------------------------------------
    # ANSWER
    # --------------------------------------------------------

    print()
    print(
        "Generating grounded answer..."
    )

    answer = generate_answer(
        question,
        results
    )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "                         ANSWER"
    )
    print("=" * 70)

    print(answer)

    if results:
        print_sources(
            results
        )

    print(
        "=" * 70
    )