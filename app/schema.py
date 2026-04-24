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
        description="Extract EVERY SINGLE line of the address exactly as written. Create a new string in this array for each line or comma-separated segment. Do not skip pincodes or landmarks.",
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
        description="Phone or mobile number(s). If multiple numbers are present, include each in a separate string in this list.",
        default=None,
    )
    emailId: Optional[str] = Field(
        description="Email address of the entity or contact person.",
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
        description="Extract EVERY SINGLE line of text describing this specific product or service exactly as written. If there are hardware serial numbers, part numbers, or multi-line descriptions, create a new string in this array for each line. Do not summarize. If a letter is in uppercase, keep it uppercase. If a letter is in lowercase, keep it lowercase.",
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
        description="The number of units sold, represented as a string (e.g., '50', '2.5').",
        default=None,
    )
    uom: Optional[str] = Field(
        description="Unit of Measurement (e.g., 'Nos', 'PCS', 'Kgs', 'Liters').",
        default=None,
    )
    unitRate: Optional[str] = Field(
        description="The price per unit before taxes and discounts, as a string up to 2 decimal places (e.g., '650.00').",
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
        description="The final calculated amount for this row, represented as a string.",
        default=None,
    )


class TaxSummary(BaseModel):
    """
    The aggregate financial breakdown usually found at the bottom of the invoice.
    """
    totalTaxableValue: str = Field(
        description="The total baseline amount upon which GST is calculated. Represented as a string."
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
        description="The final Grand Total payable amount, including all taxes and charges, represented as a string."
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
        description="The date the invoice was generated, explicitly formatted exactly as YYYY-MM-DD. Usually under 'Invoice Date' or 'Dated'.",
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
    eWayBillNumber: Optional[str] = Field(
        description="The e-Way Bill number used for the transport of goods.",
        default=None,
    )
    dispatchedThrough: Optional[str] = Field(
        description="The courier, transport agency, or delivery mode (e.g., 'BLUE DART', 'Road').",
        default=None,
    )
    docketOrLrNumber: Optional[str] = Field(
        description="The Lorry Receipt (LR) number, Railway Receipt (RR) number, or courier tracking/docket number.",
        default=None,
    )

    # PHASE 4: Transaction Details
    lineItems: List[LineItem] = Field(
        description="An array containing a record for EVERY row in the products/services table. Do not skip any items.",
        default_factory=list,
    )
    freightCharges: Optional[str] = Field(
        description="Any shipping, delivery, or freight charges added to the bill as a string.",
        default=None,
    )

    # PHASE 5: Financials & Footer
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
