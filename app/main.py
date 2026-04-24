import asyncio  # NEW: Needed for thread offloading
import os
import tempfile
import time
from contextlib import asynccontextmanager

import fitz
import instructor
import pymupdf4llm
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Marker OCR imports
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from openai import AsyncOpenAI

from app.schema import InvoiceExtraction

client = instructor.from_openai(
    AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
    ),
    mode=instructor.Mode.JSON,
)

# Global variable to hold converter and models in memory
converter_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager: Runs once when the server starts.
    We load the heavy Marker OCR models into memory here so they
    are instantly available for incoming API requests.
    """
    global converter_instance
    print("Loading Marker OCR models into memory...")
    models_dict = create_model_dict()
    converter_instance = PdfConverter(artifact_dict=models_dict)
    print("Models loaded successfully.")
    yield
    # Cleanup on shutdown
    converter_instance = None


app = FastAPI(title="Tax Invoice Parser API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace "*" with the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/extract-invoice")
async def extract_invoice(file: UploadFile = File(...)):
    allowed_extensions = (".pdf")
    filename = file.filename.lower()

    if not filename.endswith(allowed_extensions):
        raise HTTPException(
            status_code=400, detail="Only PDFs are supported."
        )

    # 5MB File Size Limit
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    file.file.seek(0, 2)  # Move cursor to end of file
    file_size = file.file.tell()  # Get current position (size)
    file.file.seek(0)  # Reset cursor back to the beginning

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail="File too large. Maximum size is 5MB."
        )

    start_time = time.time()
    tmp_file_path = None

    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_file_path = tmp.name

        # Try to parse the file using PyMuPDF (fitz)
        full_text = ""
        needs_ocr = False

        if suffix == ".pdf":
            try:
                # Quickly peek at the PDF to get the total page count
                doc = fitz.open(tmp_file_path)
                total_pages = doc.page_count
                doc.close()

                # Read a maximum of 15 pages
                pages_to_extract = list(range(min(total_pages, 15)))

                # 3. Offload PDF parsing to a background thread
                full_text = await asyncio.to_thread(
                    pymupdf4llm.to_markdown, tmp_file_path, pages=pages_to_extract
                )

                if len(full_text.strip()) < 20:
                    print(
                        "Parsing using PyMuPDFLLM yielded very little text, triggering Marker OCR"
                    )
                    needs_ocr = True
            except Exception as e:
                print(f"An error occurred while parsing the PDF using PyMuPDFLLM:\n{e}")
                needs_ocr = True
        else:
            print("PyMuPDFLLM failed to read the file since it is not a PDF.")
            needs_ocr = True

        # If the file is not a PDF or the PDF is a scanned image, use Marker OCR
        if needs_ocr:
            print(f"Triggering Marker OCR for {filename}...")
            # Offload CPU-heavy OCR to a background thread so the API doesn't freeze
            rendered = await asyncio.to_thread(converter_instance, tmp_file_path)
            full_text, _, _ = text_from_rendered(rendered)

        if not full_text or len(full_text) < 20:
            raise HTTPException(
                status_code=422, detail="Extraction using Marker Converter failed"
            )

        system_prompt = """
        You are an expert financial data extraction system tailored for Indian GST Tax Invoices.
        Extract the requested fields from the provided invoice markdown.
        CRITICAL INSTRUCTIONS:
        1. DO NOT perform any calculations. Extract numbers exactly as they appear on the document.
        2. Maintain table row integrity. Do not merge separate line items.
        3. If an entity has multiple addresses, extract the one explicitly labeled 'Billing' or 'Registered'.
        4. If a field is not explicitly present, return null. Do not guess or infer HSN codes, GSTINs, or tax rates.
        """

        candidate_data = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_model=InvoiceExtraction,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Invoice Markdown:\n\n{full_text}"},
            ],
            temperature=0.0,
        )
        candidate_data_dict = candidate_data.model_dump()

        # Post processing logic

        # Join multi-line text with newlines to preserve formatting
        for item in candidate_data_dict.get("lineItems", []):
            if item.get("description"):
                item["description"] = "\n".join(item["description"])

        address_entities = ["supplierDetails", "buyerDetails", "consigneeDetails"]
        for entity in address_entities:
            details = candidate_data_dict.get(entity)
            if details and details.get("addressLines"):
                details["addressLines"] = "\n".join(details["addressLines"])

        # 2. Update mandatory fields for Indian Invoices
        mandatory_fields = [
            "invoiceNumber",
            "invoiceDate",
            "invoiceTotalAmount"
        ]

        missing_fields = []
        # Check top level fields
        for field in mandatory_fields:
            if not candidate_data_dict.get(field):
                missing_fields.append(field)

        # Check nested supplier GSTIN
        if not candidate_data_dict.get("supplierDetails", {}).get("gstin"):
            missing_fields.append("supplierDetails.gstin")

        # Financial Validation
        tax_summary = candidate_data_dict.get("taxSummary", {})
        if not tax_summary.get("totalTaxableValue"):
            missing_fields.append("taxSummary.totalTaxableValue")

        # Check if at least one tax type was charged (or if it's an IGST vs CGST/SGST split)
        has_tax = (
            tax_summary.get("totalCgstAmount") or
            tax_summary.get("totalSgstAmount") or
            tax_summary.get("totalIgstAmount")
        )
        if not has_tax:
            missing_fields.append("taxSummary.MissingTaxBreakdown")

        processing_time = round((time.time() - start_time) * 1000)

        return {
            "status": "success",
            "processing_time_ms": processing_time,
            "missing_fields": missing_fields,
            "num_missing_fields": len(missing_fields),
            "data": candidate_data_dict,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
