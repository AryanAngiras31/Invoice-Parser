import os
import tempfile
import time
import base64

import pytesseract
from PIL import Image, ImageEnhance
import io

import fitz
import instructor
from openai import AsyncOpenAI
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.schema import InvoiceExtraction

# 1. Initialize the Groq client using Instructor
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

        # Convert ALL pages of the PDF into Base64 Images
        doc = fitz.open(tmp_file_path)
        base64_images = []
        raw_pdf_text = ""

        # Limit to 15 pages to prevent massive payloads crashing the API limit
        for page_num in range(min(doc.page_count, 15)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)      # High DPI for better OCR accuracy for serial numbers
            img_bytes = pix.tobytes("jpeg")
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            base64_images.append(base64_image)

            # Extract raw text from the image using pytesseract
            image = Image.open(io.BytesIO(img_bytes))
            # Convert to grayscale
            gray_image = image.convert('L')
            # Increase contrast to make text pop
            enhancer = ImageEnhance.Contrast(gray_image)
            high_contrast_image = enhancer.enhance(2.0)
            # Apply a slight threshold (binarization)
            bw_image = high_contrast_image.point(lambda x: 0 if x < 128 else 255, '1')
            raw_pdf_text += pytesseract.image_to_string(bw_image) + "\n\n"

        doc.close()

        system_prompt = """
        You are an expert financial data extraction system tailored for Indian GST Tax Invoices.
        Extract the requested fields using BOTH the provided images and the raw text.
        CRITICAL INSTRUCTIONS:
        1. DO NOT perform any calculations. Extract numbers exactly as they appear on the document.
        2. Maintain table row integrity. Do not merge separate line items.
        3. 3. Use the raw text provided to ensure 100% accuracy of dates, hardware serial numbers, and GSTINs. Do not guess or hallucinate characters.
        4. If a field is not explicitly present, return null. Do not guess or infer HSN codes, GSTINs, or tax rates.
        """

        print(f"raw_pdf_text: {raw_pdf_text}")

        # 3. Dynamically build the multi-image payload
        user_content = [
            {
                "type": "text",
                "text": "Extract the data from this invoice. Use the raw text below to verify exact serial numbers and dates, and use the images to understand the table layout.\n\nRAW TEXT:\n" + raw_pdf_text
            }
        ]

        for b64_img in base64_images:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_img}"
                }
            })

        # Call Vision Model Llama 4 Scout
        candidate_data = await client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            response_model=InvoiceExtraction,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0,
        )

        candidate_data_dict = candidate_data.model_dump()

        # Post processing logic

        # Update mandatory fields for Indian Invoices
        mandatory_fields = [
            "invoiceNumber",
            "invoiceDate"
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

        # Check if invoice total amount is present
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
