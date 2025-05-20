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

# Extract plain text from supported file types
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
        # Summary Prompt
        summary_prompt = (
            "You are an expert assistant tasked with summarizing official correspondence. "
            "Read the following message and return a clean, clear markdown-formatted response. "
            "Structure the output as follows:\n\n"
            "### Summary (Top of the Response)\n"
            "A short overview in bullet points.\n\n"
            "---\n\n"
            "### Date & Time\n\n"
            "Extract any date/time and format clearly.\n\n"
            "### Sender & Recipients\n"
            "- **Sender**: [Full Name]\n"
            "- **Recipients**: [List of all]\n\n"
            "### Subject\n"
            "Pull the subject from the body, if available.\n\n"
            "### Evaluation / Outcome / Decisions\n"
            "Separate key sections like evaluation, resolution, closing, and responses.\n\n"
            "### Original Translation\n"
            "Include the fully translated version of the message."
        )

        # Call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": summary_prompt},
                {"role": "user", "content": content}
            ]
        )

        markdown_result = response.choices[0].message.content.strip()
        return JSONResponse({"result": markdown_result})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
