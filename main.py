from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
import fitz  # PyMuPDF
import docx
import os

# Initialize OpenAI with environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(
    title="AI Translator API",
    description="Translate and summarize documents using GPT-4o",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware for frontend communication
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

# Text extraction function
def extract_text(file: UploadFile):
    if file.filename.endswith(".pdf"):
        doc = fitz.open(stream=file.file.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    elif file.filename.endswith(".docx"):
        doc = docx.Document(file.file)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file.filename.endswith(".txt"):
        return file.file.read().decode("utf-8")
    else:
        return ""

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
            "You are a professional document assistant. Read the following text and produce a clean, well-organized English translation "
            "with the following markdown structure:\n\n"
            "### Summary\n"
            "- Bullet points summarizing key facts or decisions\n\n"
            "---\n\n"
            "### Date & Time\n"
            "- Clearly format any mentioned dates or times\n\n"
            "### Sender & Recipients\n"
            "- **Sender**: [Extract from content]\n"
            "- **Recipients**: [Extract from content]\n\n"
            "### Subject\n"
            "- Derive the subject from the context or explicitly state if unclear\n\n"
            "### Decisions / Outcomes\n"
            "- List decisions, outcomes, or key actions clearly\n\n"
            "---\n\n"
            "### Full English Translation\n"
            "Include the entire translated body of the document in clear paragraphs."
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
