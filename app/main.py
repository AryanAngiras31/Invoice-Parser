import os
import tempfile
import time

from paddleocr import PPStructureV3
import instructor
from openai import AsyncOpenAI
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

from app.schema import InvoiceExtraction

# 1. Initialize the Groq client using Instructor (Pointing back to Llama 3.3 70B!)
client = instructor.from_openai(
    AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
    ),
    mode=instructor.Mode.JSON,
)

app = FastAPI(title="Tax Invoice Parser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Initialize PPStructureV3 Globally
# It handles PDFs, Layout Analysis, Table Recognition, and Markdown generation natively
ocr_engine = PPStructureV3(
    text_recognition_model_name="en_PP-OCRv4_mobile_rec",
    use_doc_orientation_classify=True,
    use_doc_unwarping=False,
    use_chart_recognition=False,
    use_formula_recognition=False,
    use_seal_recognition=False,
    device="cpu"
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
    MAX_FILE_SIZE = 5 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

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

        # 3. Natively parse the PDF using PPStructureV3
        # No image conversion needed. Paddle handles the PDF slice internally.
        output = ocr_engine.predict(input=tmp_file_path)

        markdown_list = []
        for res in output:
            md_info = res.markdown
            if md_info:
                markdown_list.append(md_info)

        # Concatenate all pages into a perfectly structured Markdown string
        raw_pdf_text = ocr_engine.concatenate_markdown_pages(markdown_list)

        print(f"-----------------------\nRaw_pdf_text:\n {raw_pdf_text}\n-----------------------")

        system_prompt = """
        You are an expert financial data extraction system tailored for Indian GST Tax Invoices.
        Extract the requested fields using the provided perfectly formatted Markdown text.
        CRITICAL INSTRUCTIONS:
        1. DO NOT perform any calculations. Extract numbers exactly as they appear.
        2. Maintain table row integrity. Do not merge separate line items.
        3. Pay extreme attention to dates, hardware serial numbers, and GSTINs.
        4. If a field is not explicitly present, return null. Do not guess.
        """

        # 4. Call Text-Only Llama 3.3 70B
        # Because the Markdown is so well-structured, 70B will flawlessly map it to JSON.
        candidate_data = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_model=InvoiceExtraction,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract the data from this invoice:\n\nRAW TEXT:\n{raw_pdf_text}"}
            ],
            temperature=0.0,
        )

        candidate_data_dict = candidate_data.model_dump()

        # --- Post processing logic for slashed serial numbers ---
        for item in candidate_data_dict.get("lineItems", []):
            if item.get("description"):
                item["description"] = "\n".join(item["description"])

            if item.get("hardwareSerialNumbers"):
                processed_sns = []
                for sn in item["hardwareSerialNumbers"]:
                    clean_sn = sn.replace("S/n:", "").replace("S/N:", "").strip()
                    if "/" in clean_sn:
                        split_parts = [part.strip() for part in clean_sn.split("/") if part.strip()]
                        processed_sns.extend(split_parts)
                    else:
                        processed_sns.append(clean_sn)
                item["hardwareSerialNumbers"] = processed_sns

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
