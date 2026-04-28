# Resume Parser API

An intelligent, production-ready Resume Parsing API built with **FastAPI**. It leverages hybrid extraction techniques—combining high-speed text extraction with heavy-duty OCR—and utilizes Large Language Models (LLMs) to transform unstructured resumes into structured JSON data tailored for HRMS systems.

## Features

- **Hybrid Extraction Engine**: 
    - Uses `PyMuPDF4LLM` for fast markdown extraction from text-based PDFs.
    - Automatically falls back to **Marker OCR** for scanned PDFs and images (PNG/JPG).
- **LLM-Powered Structuring**: Uses the `instructor` library with `Llama-3.3-70b` (via Groq) to accurately map resume content to a strict Pydantic schema.
- **Domain Specific**: Fine-tuned prompts for the Indian IT job market (e.g., extracting CTC in LPA, standardizing qualifications like B-TECH/MCA).
- **Async Lifespan Management**: Loads heavy machine learning models into memory once at startup for high-performance inference.
- **Dockerized**: Includes all necessary system dependencies (Tesseract, Ghostscript, OpenCV) for easy deployment.


## Prerequisites

- **Docker** and **Docker Compose** (Recommended)
- **Groq API Key**: Required for the LLM extraction layer. Get it at [console.groq.com](https://console.groq.com/).

## Environment Variables

The application requires the following environment variable to function:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your API key for Groq Cloud (to access Llama 3 models). |

## Installation & Setup

### Using Docker (Recommended)

Docker handles all system-level dependencies like Tesseract and Ghostscript automatically.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AryanAngiras31/Resume-Parser.git
   cd Resume-Parser
   ```

2. **Build and Run**:
   ```bash
   docker compose up --build
   ```

### Local Setup

If running locally without Docker, you must install system dependencies first:

1. **Install System Dependencies**:
   - **Linux**: `sudo apt install tesseract-ocr ghostscript libgl1 libglib2.0-0`
   - **macOS**: `brew install tesseract ghostscript`

2. **Install Python Packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Server**:
   ```bash
   export GROQ_API_KEY="your_key_here"
   uvicorn app.main:app --host 0.0.0.0 --port 8002
   ```

## API Usage

### Extract Resume Data

**Endpoint**: `POST /api/v1/extract-resume`

**Request**:
- `file`: Multipart file (PDF, PNG, or JPG)

**Example with cURL**:
```bash
curl -X 'POST' \
  'http://localhost:8002/api/v1/extract-resume' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@my_resume.pdf'
```

**Response**:
```json
{
  "status": "success",
  "processing_time_ms": 1250,
  "missing_fields": [
    "middleName",
    "alternateNumber",
    "preferredLocation"
  ],
  "num_missing_fields": 3,
  "data": {
    "firstName": "John",
    "middleName": null,
    "lastName": "Doe",
    "gender": "Male",
    "emailId": "john.doe@example.com",
    "contactNumber": "9876543210",
    "alternateNumber": null,
    "dateOfBirth": "1990-01-15",
    "presentAddress": "123 Main St",
    "currentLocation": "Bangalore",
    "preferredLocation": null,
    "willingToRelocate": false,
    "pincode": "560001",
    "jdId": null,
    "sourceId": null,
    "presentCompany": "Tech Solutions Inc.",
    "jobRole": "Software Engineer",
    "educationQualification": "B-TECH",
    "experienceYears": "5.0",
    "relevantExperience": "3.5",
    "noticePeriodDays": "30",
    "fixedSalaryLpa": "15.000",
    "isVariableSalary": true,
    "variableSalaryLpa": "2.000",
    "expectedCtc": "20.000",
    "employmentType": "Full-Time",
    "referredById": null,
    "isReferred": false,
    "skills": [
      { "skillName": "Python", "skillLevel": "Advanced" },
      { "skillName": "AWS Deployment", "skillLevel": "Intermediate" }
    ],
    "professionalDetails": {
      "professionalSummary": "Experienced software engineer with expertise in Python...",
      "workExperienceDetails": [
        {
          "companyName": "Tech Solutions Inc.",
          "bulletPoints": "Led a team of 5 developers to build the core platform. Implemented CI/CD pipelines reducing deployment time by 50%."
        }
      ],
      "projectDetails": "Built an open-source CLI tool for resume parsing. Contributed to multiple Python libraries.",
      "educationAndCertifications": "Bachelor of Technology from IIT Bombay. AWS Certified Solutions Architect."
    }
  }
}
```

## Architecture Note

The API utilizes a `lifespan` event to load OCR models into the global `converter_instance`. This ensures that the heavy weights for layout detection and text recognition are only loaded once, reducing request latency significantly after the initial boot.
