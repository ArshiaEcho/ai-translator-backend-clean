from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
import fitz  # PyMuPDF
import docx
import os
import logging
import re
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI with API key from environment
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(
    title="AI Translator API",
    description="Translate and summarize documents using GPT-4o",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "Translator API is up."}

@app.get("/")
def root():
    return {"message": "Welcome to the AI Translator API."}

# --- Clean File Parser ---
def extract_text(file: UploadFile):
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        try:
            pdf_bytes = file.file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                # Extract text with more careful handling
                page_text = page.get_text("text")
                # Remove non-printable characters
                page_text = ''.join(char for char in page_text if ord(char) > 31 or char in '\t\n\r')
                text += page_text + "\n"
            return text
        except Exception as e:
            return f"Error extracting PDF text: {str(e)}"

    elif filename.endswith(".docx"):
        contents = BytesIO(file.file.read())
        doc = docx.Document(contents)
        return "\n".join([para.text for para in doc.paragraphs])

    elif filename.endswith(".txt"):
        return file.file.read().decode("utf-8")

    else:
        return ""

def sanitize_content(content):
    """Clean and prepare text for AI processing."""
    # Check for PDF header
    if '%PDF' in content[:100]:
        logger.warning("Content appears to contain PDF header markers")
    
    # Clean up PDF artifacts with regex
    # Remove PDF stream metadata (commonly causes gibberish)
    content = re.sub(r'%PDF-\d+\.\d+', '', content)
    content = re.sub(r'\d+ \d+ obj.*?endobj', ' ', content, flags=re.DOTALL)
    content = re.sub(r'stream.*?endstream', ' ', content, flags=re.DOTALL)
    content = re.sub(r'/Filter\s*/\w+', ' ', content)
    content = re.sub(r'/Length\s*\d+', ' ', content)
    
    # Fix the specific artifacts seen in the screenshot
    pdf_artifacts = [
        'stream', 'endobj', 'obj', 'endstream', '/Filter', '/FlateDecode', 
        '/Length', '/Stream', '/Type', '%PDF-1.7', 'xref', 'trailer'
    ]
    cleaned = content
    for artifact in pdf_artifacts:
        if artifact in cleaned:
            cleaned = cleaned.replace(artifact, ' ')
    
    # Remove non-printable characters except whitespace
    cleaned = ''.join(c if (c.isprintable() or c.isspace()) else ' ' for c in cleaned)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Check if there's still binary data and take more aggressive measures if needed
    if len(cleaned) > 100:
        non_ascii_ratio = sum(1 for c in cleaned[:1000] if ord(c) > 127) / min(len(cleaned), 1000)
        if non_ascii_ratio > 0.2:  # Lower threshold to be more aggressive
            logger.warning(f"Content contains high proportion of non-ASCII (ratio: {non_ascii_ratio:.2f})")
            # More aggressive cleaning - keep only letters, numbers, and basic punctuation
            cleaned = re.sub(r'[^\w\s.,;:!?()-]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Return at least a truncated version if it's still too long
    max_length = 50000  # GPT-4 context limit is ~8k tokens, ~32k chars
    if len(cleaned) > max_length:
        logger.warning(f"Truncating content from {len(cleaned)} to {max_length} chars")
        return cleaned[:max_length]
    
    return cleaned

# --- Main Translate Route ---
@app.post("/translate")
async def translate(file: UploadFile = File(None), text: str = Form(None)):
    if file:
        logger.info(f"Received file: {file.filename}, content-type: {file.content_type}")
        content = extract_text(file)
        logger.info(f"Extracted text length: {len(content)} chars")
        if len(content) < 200:  # Log a small preview if extraction seems problematic
            logger.info(f"Text preview: {content[:200]}")
    elif text:
        logger.info(f"Received direct text input of length: {len(text)}")
        content = text
    else:
        logger.warning("No content received")
        return JSONResponse({"error": "No content received"}, status_code=400)

    if not content.strip():
        logger.warning("Empty or unsupported file.")
        return JSONResponse({"error": "Empty or unsupported file."}, status_code=422)

    try:
        # Sanitize content to remove binary data and prepare for AI processing
        cleaned_content = sanitize_content(content)
        logger.info(f"Sanitized content length: {len(cleaned_content)} chars")
        
        prompt = (
            "You are a professional document assistant. Read the following content and return a clean, clear markdown output with:\n\n"
            "### Summary\n"
            "- Bullet point summary of key points\n\n"
            "---\n\n"
            "### Date & Time\n"
            "- Extract and format any dates/times\n\n"
            "### Sender & Recipients\n"
            "- **Sender**: [Extracted name]\n"
            "- **Recipients**: [Extracted names]\n\n"
            "### Subject\n"
            "- Extracted subject or inferred topic\n\n"
            "### Decisions / Outcomes\n"
            "- List of decisions, evaluations, or conclusions\n\n"
            "---\n\n"
            "### Full English Translation\n"
            "The complete translated document, broken into clear paragraphs."
        )

        logger.info("Sending request to OpenAI")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": cleaned_content}
            ]
        )

        result = response.choices[0].message.content.strip()
        logger.info(f"Received response from OpenAI, length: {len(result)}")
        return JSONResponse({"result": result})

    except Exception as e:
        logger.error(f"Error in translation process: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/debug-pdf")
async def debug_pdf(file: UploadFile = File(...)):
    """Endpoint to diagnose PDF extraction issues without using OpenAI."""
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"error": "Only PDF files are supported by this endpoint"}, status_code=400)
    
    try:
        # Extract raw text
        pdf_bytes = file.file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        result = {
            "filename": file.filename,
            "num_pages": len(doc),
            "metadata": dict(doc.metadata),
            "page_samples": []
        }
        
        # Get sample text from each page
        for i, page in enumerate(doc):
            if i < 3:  # Just sample first 3 pages
                text = page.get_text("text")
                sample = text[:500] + "..." if len(text) > 500 else text
                
                # Count problematic characters
                non_ascii = sum(1 for c in text if ord(c) > 127)
                non_printable = sum(1 for c in text if not c.isprintable() and not c.isspace())
                
                result["page_samples"].append({
                    "page_num": i+1,
                    "text_length": len(text),
                    "sample": sample,
                    "non_ascii_count": non_ascii,
                    "non_ascii_ratio": non_ascii / max(len(text), 1),
                    "non_printable_count": non_printable,
                    "likely_binary": non_printable > len(text) * 0.1
                })
        
        # Run the text through our sanitization function
        full_text = "\n".join([page.get_text() for page in doc])
        sanitized = sanitize_content(full_text)
        
        # Include sanitization results
        result["original_length"] = len(full_text)
        result["sanitized_length"] = len(sanitized)
        result["sanitized_sample"] = sanitized[:1000] + "..." if len(sanitized) > 1000 else sanitized
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Error in PDF debugging: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)
