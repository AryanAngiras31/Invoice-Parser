import os
# --- CRITICAL: MUST BE TOP-LEVEL ---
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

import tempfile
import time
from paddleocr import PaddleOCR
import instructor
from openai import AsyncOpenAI
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.schema import InvoiceExtraction

# initialize client
client = instructor.from_openai(
    AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
    ),
    mode=instructor.Mode.JSON,
)

app = FastAPI(title="Tax Invoice Parser API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# initialize PaddleOCR for CPU
ocr_engine = PaddleOCR(device="cpu")

@app.post("/api/v1/extract-invoice")
async def extract_invoice(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDFs are supported.")

    start_time = time.time()
    tmp_file_path = None

    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_file_path = tmp.name

        # OCR using PaddleOCR
        # In PaddleOCR 3.0, we use .predict() which returns a Result object
        result = ocr_engine.predict(input=tmp_file_path)

        raw_pdf_text = ""
        for res in result:
            # The 3.0 Result object exposes a .json dictionary containing the data
            res_dict = res.json

            # Safely navigate to the 'rec_texts' array inside the 'res' object
            texts = res_dict.get("res", {}).get("rec_texts", [])

            if texts:
                # Join all the recognized text segments with a space
                raw_pdf_text += " ".join(texts) + "\n\n"
            else:
                print("Warning: Could not find 'rec_texts' in this page's output.")

        print(f"-----------------------\nRaw_pdf_text:\n {raw_pdf_text}\n-----------------------")

        system_prompt = """
        You are an expert financial data extraction system tailored for Indian GST Tax Invoices.
        Extract the requested fields using the provided raw text.
        CRITICAL INSTRUCTIONS:
        1. DO NOT perform any calculations. Extract numbers exactly as they appear.
        2. Maintain table row integrity. Do not merge separate line items.
        3. Pay extreme attention to dates, hardware serial numbers, and GSTINs.
        4. If a field is not explicitly present, return null. Do not guess.
        """

        # LLM extraction to JSON
        candidate_data = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_model=InvoiceExtraction,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"RAW TEXT FROM OCR:\n{raw_pdf_text}"}
            ],
            temperature=0.0,
        )

        candidate_data_dict = candidate_data.model_dump()

        # Update mandatory fields for Indian Invoices
        mandatory_fields = [
            "invoiceNumber",
            "invoiceDate"
        ]

        missing_fields = []
        for field in mandatory_fields:
            if not candidate_data_dict.get(field):
                missing_fields.append(field)

        if not candidate_data_dict.get("supplierDetails", {}).get("gstin"):
            missing_fields.append("supplierDetails.gstin")

        tax_summary = candidate_data_dict.get("taxSummary", {})
        if not tax_summary.get("totalTaxableValue"):
            missing_fields.append("taxSummary.totalTaxableValue")

        has_tax = (
            tax_summary.get("totalCgstAmount") or
            tax_summary.get("totalSgstAmount") or
            tax_summary.get("totalIgstAmount")
        )
        if not has_tax:
            missing_fields.append("taxSummary.MissingTaxBreakdown")

        if not candidate_data_dict.get("taxSummary", {}).get("invoiceTotalAmount"):
            missing_fields.append("taxSummary.invoiceTotalAmount")

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
