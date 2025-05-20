from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
import fitz  # PyMuPDF
import docx
import os
from io import BytesIO

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
        pdf_bytes = file.file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return "\n".join([page.get_text() for page in doc])

    elif filename.endswith(".docx"):
        contents = BytesIO(file.file.read())
        doc = docx.Document(contents)
        return "\n".join([para.text for para in doc.paragraphs])

    elif filename.endswith(".txt"):
        return file.file.read().decode("utf-8")

    else:
        return ""

# --- Main Translate Route ---
@app.post("/translate")
async def translate(file: UploadFile = File(None), text: str = Form(None)):
    if file:
        content = extract_text(file)
    elif text:
        content = text
    else:
        return JSONResponse({"error": "No content received"}, status_code=400)

    if not content.strip():
        return JSONResponse({"error": "Empty or unsupported file."}, status_code=422)

    try:
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

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ]
        )

        result = response.choices[0].message.content.strip()
        return JSONResponse({"result": result})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
