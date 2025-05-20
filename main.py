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
    description="Translate and summarize documents using GPT-4",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS for frontend/Bolt
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ping endpoint
@app.get("/ping")
def ping():
    return {"status": "ok", "message": "Translator API is up."}

# Root
@app.get("/")
def root():
    return {"message": "Welcome to the AI Translator API."}

# Text extractor
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
        # Summary
        summary_resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Summarize this document in structured bullet points or sections."},
                {"role": "user", "content": content}
            ]
        )
        summary = summary_resp.choices[0].message.content

        # Translation
        translation_resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Translate this document to English."},
                {"role": "user", "content": content}
            ]
        )
        translation = translation_resp.choices[0].message.content

        result = f"### Summary\n\n{summary}\n\n---\n\n### Translation\n\n{translation}"
        return JSONResponse({"result": result})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
