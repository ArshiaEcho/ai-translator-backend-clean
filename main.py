from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
import fitz  # PyMuPDF
import docx
import os
import traceback

# Initialize OpenAI client with environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(
    title="AI Translator API",
    description="Translate and summarize documents using GPT-4o",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Enable CORS for frontend requests
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

# Function to extract clean text from uploaded file
def extract_text(file: UploadFile):
    try:
        if file.filename.endswith(".pdf"):
            pdf_bytes = file.file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            return "\n".join([page.get_text("text") for page in doc])
        elif file.filename.endswith(".docx"):
            doc = docx.Document(file.file)
            return "\n".join([para.text for para in doc.paragraphs])
        elif file.filename.endswith(".txt"):
            return file.file.read().decode("utf-8")
        else:
            return ""
    except Exception as e:
        print("Error reading file:", e)
        traceback.print_exc()
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
            "- **Sender**: [Extracted from content]\n"
            "- **Recipients**: [Extracted from content]\n\n"
            "### Subject\n"
            "- Derive the subject from context or explicitly state if unclear\n\n"
            "### Decisions / Outcomes\n"
            "- List decisions, resolutions, or important actions\n\n"
            "---\n\n"
            "### Full English Translation\n"
            "Include the full translated document content in clear, natural paragraphs."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ]
        )

        output = response.choices[0].message.content.strip()
        return JSONResponse({"result": output})

    except Exception as e:
        print("Translation failed:", e)
        traceback.print_exc()
        return JSONResponse({"error": f"Translation failed: {str(e)}"}, status_code=500)
