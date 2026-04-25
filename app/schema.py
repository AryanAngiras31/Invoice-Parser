from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class EntityDetails(BaseModel):
    """
    Reusable schema for Supplier, Buyer (Bill To), and Consignee (Ship To) details.
    """
    entityName: str = Field(
        description="The exact legal name of the business or individual. Convert to Title Case."
    )
    addressLines: List[str] = Field(
        description="Extract EVERY SINGLE line of the address exactly as written. Create a new string in this array for each line or comma-separated segment. Do not skip pincodes or landmarks. Do not include the Phone number (Ph.No.), GSTIN, State Name, Contact or Email here. ",
        default_factory=list,
    )
    gstin: Optional[str] = Field(
        description="The 15-character GST Identification Number (GSTIN). Return null if not present.",
        default=None,
    )
    pan: Optional[str] = Field(
        description="The 10-character Permanent Account Number (PAN). Often embedded inside the GSTIN or listed separately. Return null if not present.",
        default=None,
    )
    stateName: Optional[str] = Field(
        description="The name of the state (e.g., 'Karnataka', 'Delhi'). Convert to Title Case.",
        default=None,
    )
    stateCode: Optional[str] = Field(
        description="The 2-digit numerical GST state code (e.g., '29', '06').",
        default=None,
    )
    contactPerson: Optional[str] = Field(
        description="The name of the specific contact person mentioned under this entity, if any.",
        default=None,
    )
    contactNumber: Optional[List[str]] = Field(
        description="Phone or mobile number(s). If multiple numbers are present, include each in a separate string in this list. The field is usually listed as 'Contact Number', 'Contact' or 'Ph.No.'.",
        default=None,
    )
    emailId: Optional[str] = Field(
        description="Email address of the entity or contact person.",
        default=None,
    )

class DeliveryDetails(BaseModel):
    """
    Logistics, shipping, and delivery information.
    """
    deliveryNote: Optional[str] = Field(
        description="The Delivery Note identifier. Return null if not present.",
        default=None,
    )
    deliveryNoteDate: Optional[str] = Field(
        description="The date of the delivery note, formatted as YYYY-MM-DD if possible. Return null if not present.",
        default=None,
    )
    eWayBillNumber: Optional[str] = Field(
        description="The e-Way Bill number used for the transport of goods. Return null if not present.",
        default=None,
    )
    dispatchedThrough: Optional[str] = Field(
        description="The courier, transport agency, or delivery mode (e.g., 'BLUE DART', 'Road'). Return null if not present.",
        default=None,
    )
    dispatchDocumentNumber: Optional[str] = Field(
        description="The Dispatch Document No., Lorry Receipt (LR) number, Railway Receipt (RR) number, or Docket number. Return null if not present.",
        default=None,
    )
    destination: Optional[str] = Field(
        description="The final destination city or location for the delivery (e.g., 'GURGAON', 'Bengaluru'). Return null if not present.",
        default=None,
    )
    motorVehicleNumber: Optional[str] = Field(
        description="The vehicle registration or license plate number (e.g., 'KA51AG8938'). Return null if not present.",
        default=None,
    )
    termsOfDelivery: Optional[str] = Field(
        description="Specific terms and conditions relating to the physical delivery of goods. Return null if not present.",
        default=None,
    )
    receiverName: Optional[str] = Field(
        description="Name of the specific person or entity receiving the shipment/courier, often listed under courier details. Return null if not present.",
        default=None,
    )

class LineItem(BaseModel):
    """
    Represents a single row in the invoice's product or service table.
    """
    serialNumber: Optional[str] = Field(
        description="The sequence or serial number of the item in the table (e.g., '1', '2', 'A').",
        default=None,
    )
    description: List[str] = Field(
        description="Extract the first line of text (usually right next to the serial number) describing this specific product or service exactly as written. Do not summarize. If a letter is in uppercase, keep it uppercase. If a letter is in lowercase, keep it lowercase. Do not include hardware serial numbers such as 'BBR01913354100310'",
        default_factory=list,
    )
    hardwareSerialNumbers: List[str] = Field(
        description="Hardware serial numbers are long alphanumeric codes present below the description of the product or service. Extract EVERY SINGLE hardware serial number (Eg: 'AM150G6T', 'BBR01913354100310') associated with this line item. If two serial numbers are on the same line (Eg: 'AH0FBEPCPAB97E 5AH0FBEPCABA443'), extract both as separate serial numbers. Extract all alphanumeric serial codes even if the 'S/n' prefix is omitted. Return the serial numbers exactly as present. Do not hallucinate any serial numbers that are not present on the document.",
        default_factory=list,
    )
    modelNumber: Optional[str] = Field(
        description="The model number or part number of the product or service. If a letter is in uppercase, keep it uppercase. If a letter is in lowercase, keep it lowercase. Return null if not present",
        default=None,
    )
    hsnSacCode: Optional[str] = Field(
        description="The HSN (Harmonized System of Nomenclature) or SAC (Services Accounting Code) assigned to this item. Usually a 4 to 8 digit number.",
        default=None,
    )
    quantity: Optional[str] = Field(
        description="The number of units sold. Extract ONLY the numeric value. Do NOT include text labels (like 'Nos' or 'PCS') in this field.",
        default=None,
    )
    uom: Optional[str] = Field(
        description="Unit of Measurement (e.g., 'Nos', 'PCS', 'Kgs', 'Liters').",
        default=None,
    )
    unitRate: Optional[str] = Field(
        description="The price per unit before taxes and discounts. Extract ONLY the numeric value up to 2 decimal places. Do NOT include currency symbols (like ₹ or Rs).",
        default=None,
    )
    discountAmount: Optional[str] = Field(
        description="The monetary value or percentage of discount applied to this specific line item, if explicitly stated.",
        default=None,
    )
    gstRatePercentage: Optional[str] = Field(
        description="The combined GST percentage rate applied to this item (e.g., '18%', '9%').",
        default=None,
    )
    itemTotalAmount: Optional[str] = Field(
        description="The final calculated amount for this row. Extract ONLY the numeric value. Do NOT include currency symbols.",
        default=None,
    )

class TaxSummary(BaseModel):
    """
    The aggregate financial breakdown usually found at the bottom of the invoice.
    """
    totalTaxableValue: str = Field(
        description="The total baseline amount upon which GST is calculated. Represented as a string. Extract ONLY the numeric value."
    )
    totalCgstAmount: Optional[str] = Field(
        description="The aggregate Central GST amount charged on the invoice as a string. Return null if not applicable.",
        default=None,
    )
    cgstPercentage: Optional[str] = Field(
        description="The percentage of the total taxable value that is charged as Central GST. Return null if not applicable.",
        default=None,
    )
    totalSgstAmount: Optional[str] = Field(
        description="The aggregate State (or UT) GST amount charged on the invoice as a string. Return null if not applicable.",
        default=None,
    )
    sgstPercentage: Optional[str] = Field(
        description="The percentage of the total taxable value that is charged as State (or UT) GST. Return null if not applicable.",
        default=None,
    )
    totalIgstAmount: Optional[str] = Field(
        description="The aggregate Integrated GST amount charged on the invoice as a string. Return null if not applicable.",
        default=None,
    )
    igstPercentage: Optional[str] = Field(
        description="The percentage of the total taxable value that is charged as Integrated GST. Return null if not applicable.",
        default=None,
    )
    roundingOff: Optional[str] = Field(
        description="Any fractional adjustment made to round the grand total (e.g., '0.50', '-0.16').",
        default=None,
    )
    invoiceTotalAmount: str = Field(
        description="The final Grand Total payable amount, including all taxes and charges. Extract ONLY the numeric value without currency symbols."
    )
    amountInWords: Optional[str] = Field(
        description="The exact text where the grand total or tax amount is written out alphabetically.",
        default=None,
    )

class BankDetails(BaseModel):
    """
    Supplier's banking information for payment processing.
    """
    bankName: Optional[str] = Field(
        description="The name of the banking institution (e.g., 'ICICI Bank', 'Axis Bank').",
        default=None,
    )
    accountNumber: Optional[str] = Field(
        description="The bank account number for remittance.",
        default=None,
    )
    ifscCode: Optional[str] = Field(
        description="The 11-character Indian Financial System Code (IFSC) for the bank branch.",
        default=None,
    )
    branchName: Optional[str] = Field(
        description="The name or location of the bank branch.",
        default=None,
    )

class InvoiceExtraction(BaseModel):
    """
    Schema for completely extracting and structuring an Indian B2B/B2C Tax Invoice.
    """
    # PHASE 1: Document Metadata
    documentType: Literal["Tax Invoice", "Bill of Supply", "Proforma Invoice", "Unknown"] = Field(
        description="Identify the nature of the document. Default to 'Unknown' if unclear."
    )
    invoiceNumber: str = Field(
        description="The unique document identifier/invoice number. Usually under 'Invoice Number' or 'Invoice No.'."
    )
    invoiceDate: Optional[str] = Field(
        description="The date the invoice was generated, explicitly formatted exactly as YYYY-MM-DD. Usually under 'Invoice Date' or 'Dated'. Do not default to 23 or 24. Take this data from the raw text attached.",
        default=None,
    )
    irn: Optional[str] = Field(
        description="The 64-character Invoice Reference Number (IRN) generated for E-Invoices. It may be split into multiple lines by a '-' return the full concatenated string.",
        default=None,
    )
    acknowledgementNumber: Optional[str] = Field(
        description="The e-Invoice Ack No., if present.",
        default=None,
    )

    # PHASE 2: Identity Context
    supplierDetails: EntityDetails = Field(
        description="The entity issuing the invoice and selling the goods/services."
    )
    buyerDetails: EntityDetails = Field(
        description="The entity billed for the goods/services (Bill To)."
    )
    consigneeDetails: Optional[EntityDetails] = Field(
        description="The entity receiving the goods (Ship To). Often the same as the buyer. Return null if a separate 'Ship To' is not explicitly mentioned.",
        default=None,
    )

    # PHASE 3: Order & Shipping Logistics
    poNumber: Optional[str] = Field(
        description="The Buyer's Purchase Order (PO) number, reference number or sale order number.",
        default=None,
    )
    paymentTerms: Optional[str] = Field(
        description="The agreed terms of payment (e.g., '30 Days Credit', 'COD - 15 days PDC').",
        default=None,
    )
    paymentDueDate: Optional[str] = Field(
        description="The specific deadline for payment, formatted as YYYY-MM-DD if available.",
        default=None,
    )

    # PHASE 4: Transaction Details
    deliveryDetails: Optional[DeliveryDetails] = Field(
        description="Details regarding the physical dispatch, transport, and delivery of the goods. Return null if no shipping or dispatch information is present.",
        default=None,
    )

    # PHASE 5: Transaction Details
    lineItems: List[LineItem] = Field(
        description="An array containing a record for EVERY row in the products/services table. Do not skip any items.",
        default_factory=list,
    )
    freightCharges: Optional[str] = Field(
        description="Any shipping, delivery, or freight charges added to the bill as a string. Extract ONLY the numeric value.",
        default=None,
    )

    # PHASE 6: Financials & Footer
    taxSummary: TaxSummary = Field(
        description="The final aggregated financial calculations for the invoice."
    )
    bankDetails: Optional[BankDetails] = Field(
        description="The supplier's banking information.",
        default=None,
    )
    termsAndConditions: List[str] = Field(
        description="Extract EVERY SINGLE bullet point or sentence under 'Terms & Conditions', 'Declaration', or 'Disclaimer' exactly as written. Create a new string in this array for each condition.",
        default_factory=list,
    )
    reverseChargeApplicable: Literal["Yes", "No", "NA"] = Field(
        description="Determine if reverse charge mechanism is applicable based on text or checkboxes. Default to 'NA' if not mentioned.",
        default="NA",
    )
