# Tax Invoice Parser API

An intelligent, production-ready Tax Invoice Parsing API built with **FastAPI**. It leverages OCR (Optical Character Recognition) combined with Large Language Models (LLMs) to transform unstructured Indian GST Tax Invoices into structured JSON data tailored for accounting and compliance systems.

## Features

- **OCR-Based Extraction**: 
    - Uses **PaddleOCR** for robust text extraction from scanned PDFs and images.
    - Optimized for Indian GST invoice layouts and formats.
- **LLM-Powered Structuring**: Uses the `instructor` library with `Llama-3.3-70b` (via Groq) to accurately map invoice content to a strict Pydantic schema.
- **Domain Specific**: Fine-tuned prompts for Indian GST Tax Invoices (e.g., extracting GSTIN, HSN/SAC codes, CGST/SGST/IGST breakdowns).
- **Comprehensive Data Extraction**: Captures supplier details, buyer details, line items, tax summaries, bank details, and delivery information.
- **Dockerized**: Includes all necessary system dependencies for easy deployment.


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

Docker handles all system-level dependencies automatically.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AryanAngiras31/Invoice-Parser.git
   cd Invoice-Parser
   ```

2. **Build and Run**:
   ```bash
   docker compose up --build
   ```

### Local Setup

If running locally without Docker:

1. **Install Python Packages**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Server**:
   ```bash
   export GROQ_API_KEY="your_key_here"
   uvicorn app.main:app --host 0.0.0.0 --port 8002
   ```

## API Usage

### Extract Invoice Data

**Endpoint**: `POST /api/v1/extract-invoice`

**Request**:
- `file`: Multipart file (PDF only)

**Example with cURL**:
```bash
curl -X 'POST' \
  'http://localhost:8002/api/v1/extract-invoice' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@tax_invoice.pdf'
```

**Response**:
```json
{
  "status": "success",
  "processing_time_ms": 3200,
  "missing_fields": [
    "irn",
    "deliveryDetails.eWayBillNumber"
  ],
  "num_missing_fields": 2,
  "data": {
    "documentType": "Tax Invoice",
    "invoiceNumber": "GST/2024/001234",
    "invoiceDate": "2024-01-15",
    "irn": null,
    "acknowledgementNumber": null,
    "supplierDetails": {
      "entityName": "ABC Technologies Pvt Ltd",
      "addressLines": ["123 Industrial Area", "Phase 2, Whitefield"],
      "gstin": "29AABCU9603R1ZM",
      "pan": "AABCU9603R",
      "stateName": "Karnataka",
      "stateCode": "29",
      "contactPerson": "Rajesh Kumar",
      "contactNumber": ["+91-80-12345678"],
      "emailId": "accounts@abctech.com"
    },
    "buyerDetails": {
      "entityName": "XYZ Enterprises Ltd",
      "addressLines": ["456 Business Park", "Sector 5, Gurgaon"],
      "gstin": "06AAACX1234Y1Z5",
      "pan": "AAACX1234Y",
      "stateName": "Haryana",
      "stateCode": "06",
      "contactPerson": "Priya Sharma",
      "contactNumber": ["+91-98-76543210"],
      "emailId": "procurement@xyzent.com"
    },
    "consigneeDetails": null,
    "poNumber": "PO/2024/456",
    "paymentTerms": "30 Days Credit",
    "paymentDueDate": "2024-02-14",
    "deliveryDetails": {
      "deliveryNote": "DN/2024/123",
      "deliveryNoteDate": "2024-01-15",
      "eWayBillNumber": null,
      "dispatchedThrough": "BLUE DART",
      "dispatchDocumentNumber": "BD123456789",
      "destination": "GURGAON",
      "motorVehicleNumber": "HR26AB1234",
      "termsOfDelivery": "Door Delivery",
      "receiverName": "Warehouse Manager"
    },
    "lineItems": [
      {
        "serialNumber": "1",
        "description": ["Dell Latitude Laptop 7430"],
        "hardwareSerialNumbers": ["SN123456789", "SN987654321"],
        "modelNumber": "LAT7430-I7-16GB",
        "hsnSacCode": "8471.30",
        "quantity": "10",
        "uom": "Nos",
        "unitRate": "75000.00",
        "discountAmount": "5%",
        "gstRatePercentage": "18%",
        "itemTotalAmount": "708750.00"
      }
    ],
    "freightCharges": "2500.00",
    "taxSummary": {
      "totalTaxableValue": "708750.00",
      "totalCgstAmount": "63787.50",
      "cgstPercentage": "9%",
      "totalSgstAmount": "63787.50",
      "sgstPercentage": "9%",
      "totalIgstAmount": null,
      "igstPercentage": null,
      "roundingOff": "0.00",
      "invoiceTotalAmount": "838825.00",
      "amountInWords": "Rupees Eight Lakh Thirty Eight Thousand Eight Hundred Twenty Five Only"
    },
    "bankDetails": {
      "bankName": "ICICI Bank",
      "accountNumber": "123456789012",
      "ifscCode": "ICIC0000123",
      "branchName": "Whitefield Branch"
    },
    "termsAndConditions": [
      "Goods once sold will not be taken back.",
      "Interest @18% p.a. will be charged on overdue invoices."
    ],
    "reverseChargeApplicable": "No"
  }
}
```

## Architecture Note

The API initializes the **PaddleOCR** engine at startup, loading the OCR models into memory once. This ensures that the heavy weights for text detection and recognition are only loaded once, reducing request latency significantly after the initial boot.
