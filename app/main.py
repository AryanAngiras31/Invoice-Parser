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

# 1. Initialize Groq
client = instructor.from_openai(
    AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
    ),
    mode=instructor.Mode.JSON,
)

app = FastAPI(title="Tax Invoice Parser API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 2. CORRECT INITIALIZATION FOR PaddleOCR 3.0
# The 3.0 base class is extremely light. No charts, no formulas.
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

        # 3. CORRECT OCR METHOD CALL FOR 3.0
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

        # 4. LLM EXTRACTION
        candidate_data = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_model=InvoiceExtraction,
            messages=[
                {"role": "system", "content": "Extract Indian GST invoice data. Pay close attention to serial numbers and GSTINs."},
                {"role": "user", "content": f"RAW TEXT FROM OCR:\n{raw_pdf_text}"}
            ],
            temperature=0.0,
        )

        candidate_data_dict = candidate_data.model_dump()

        # Post-processing logic for slashed serial numbers
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

        return {
            "status": "success",
            "processing_time_ms": round((time.time() - start_time) * 1000),
            "data": candidate_data_dict,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
