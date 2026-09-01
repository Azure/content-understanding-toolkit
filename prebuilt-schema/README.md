# Prebuilt Schema Definitions

This directory documents the field schemas produced by Azure Content Understanding's prebuilt document analyzers. Use this page to find the right prebuilt analyzer for a document, then follow the link to see its exact schema (field name, type, extraction method, description, and example).

## How to use this index (including for agents)

- Every analyzer has an **analyzer ID**. To call it through the Content Understanding API, prefix the ID with `prebuilt-` (for example, category `receipt.generic` -> analyzer ID `prebuilt-receipt.generic`).
- Categories that group multiple document sub-types (mortgage, procurement, receipt, tax) have an index page (e.g. [`tax.us/tax.us.md`](2025-11-01/tax.us/tax.us.md)) listing each sub-type, its analyzer ID, and a description to help pick the closest match.
- When classifying a document of unknown type, prefer the most specific matching category. If nothing matches, fall back to `other` (analyzer ID `prebuilt-documentFields`, schema [`documentFieldSchema.md`](2025-11-01/documentFieldSchema.md)), which returns a proposed schema instead of fixed fields.
- Pick an API version folder based on the API version you're targeting:
  - [`2025-11-01/`](2025-11-01) — stable, generally available schemas.
  - [`2026-06-01-preview/`](2026-06-01-preview) — preview schemas. Adds an index page per tax form and year-versioned analyzers (e.g. `tax.us.1040.2025`, analyzer ID `prebuilt-tax.us.1040.2025`) alongside the non-versioned analyzer, plus the additional `tax.us.mn.m1` category.

## Categories

### General document fields

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `documentFieldSchema` | `prebuilt-documentFields` | [link](2025-11-01/documentFieldSchema.md) | [link](2026-06-01-preview/documentFieldSchema.md) | Fallback analyzer that proposes a field schema for a document that doesn't match any other category. |

### Financial documents

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `bankStatement.us` | `prebuilt-bankStatement.us` | [link](2025-11-01/bankStatement.us.md) | [link](2026-06-01-preview/bankStatement.us.md) | U.S. bank statement; account holder/bank details, statement period, per-account balances and transactions. |
| `check.us` | `prebuilt-check.us` | [link](2025-11-01/check.us.md) | [link](2026-06-01-preview/check.us.md) | U.S. personal or business check; payer/payee, amount (numeric and in words), MICR line, signature presence. |
| `creditCard` | `prebuilt-creditCard` | [link](2025-11-01/creditCard.md) | [link](2026-06-01-preview/creditCard.md) | Payment card; card number, issuing bank, payment network, cardholder name, validity dates, customer service numbers. |
| `payStub.us` | `prebuilt-payStub.us` | [link](2025-11-01/payStub.us.md) | [link](2026-06-01-preview/payStub.us.md) | U.S. pay stub; employee/employer details, pay period, current and year-to-date gross pay, taxes, deductions, net pay. |

### Identity documents

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `idDocument` (index) | — | [link](2025-11-01/idDocument/idDocument.md) | [link](2026-06-01-preview/idDocument/idDocument.md) | Index of identity document sub-types. |
| `idDocument.generic` | `prebuilt-idDocument.generic` | [link](2025-11-01/idDocument/idDocument.generic.md) | [link](2026-06-01-preview/idDocument/idDocument.generic.md) | Government-issued ID cards/permits other than passports (driver's license, national ID, residence permit, etc.). |
| `idDocument.passport` | `prebuilt-idDocument.passport` | [link](2025-11-01/idDocument/idDocument.passport.md) | [link](2026-06-01-preview/idDocument/idDocument.passport.md) | Passport booklets and passport cards. |

### Insurance & vital records

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `healthInsuranceCard.us` | `prebuilt-healthInsuranceCard.us` | [link](2025-11-01/healthInsuranceCard.us.md) | [link](2026-06-01-preview/healthInsuranceCard.us.md) | U.S. health insurance card; insurer, member, dependents, plan, copays, prescription and Medicare/Medicaid info. |
| `marriageCertificate.us` | `prebuilt-marriageCertificate.us` | [link](2025-11-01/marriageCertificate.us.md) | [link](2026-06-01-preview/marriageCertificate.us.md) | U.S. marriage certificate; both spouses' details, document number, issue and marriage date/place. |

### Legal documents

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `contract` | `prebuilt-contract` | [link](2025-11-01/contract.md) | [link](2026-06-01-preview/contract.md) | Legal contract; title, contract ID, parties, execution/effective/expiration/renewal dates, duration, jurisdictions. |

### Mortgage (US)

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `mortgage.us` (index) | — | [link](2025-11-01/mortgage.us/mortgage.us.md) | [link](2026-06-01-preview/mortgage.us/mortgage.us.md) | Index of U.S. mortgage document sub-types. |
| `mortgage.us.1003` | `prebuilt-mortgage.us.1003` | [link](2025-11-01/mortgage.us/mortgage.us.1003.md) | [link](2026-06-01-preview/mortgage.us/mortgage.us.1003.md) | Uniform Residential Loan Application (URLA). |
| `mortgage.us.1004` | `prebuilt-mortgage.us.1004` | [link](2025-11-01/mortgage.us/mortgage.us.1004.md) | [link](2026-06-01-preview/mortgage.us/mortgage.us.1004.md) | Uniform Residential Appraisal Report (URAR). |
| `mortgage.us.1005` | `prebuilt-mortgage.us.1005` | [link](2025-11-01/mortgage.us/mortgage.us.1005.md) | [link](2026-06-01-preview/mortgage.us/mortgage.us.1005.md) | Verification of Employment (VOE). |
| `mortgage.us.1008` | `prebuilt-mortgage.us.1008` | [link](2025-11-01/mortgage.us/mortgage.us.1008.md) | [link](2026-06-01-preview/mortgage.us/mortgage.us.1008.md) | Transmittal Summary (underwriting summary). |
| `mortgage.us.closingDisclosure` | `prebuilt-mortgage.us.closingDisclosure` | [link](2025-11-01/mortgage.us/mortgage.us.closingDisclosure.md) | [link](2026-06-01-preview/mortgage.us/mortgage.us.closingDisclosure.md) | TILA-RESPA Closing Disclosure (TRID). |

### Procurement

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `procurement` (index) | — | [link](2025-11-01/procurement/procurement.md) | [link](2026-06-01-preview/procurement/procurement.md) | Index of procurement document sub-types. |
| `invoice` | `prebuilt-invoice` | [link](2025-11-01/procurement/invoice.md) | [link](2026-06-01-preview/procurement/invoice.md) | Seller-issued billing document requesting payment for goods or services. |
| `purchaseOrder` | `prebuilt-purchaseOrder` | [link](2025-11-01/procurement/purchaseOrder.md) | [link](2026-06-01-preview/procurement/purchaseOrder.md) | Buyer-issued ordering document authorizing a vendor to provide goods or services. |
| `utilityBill` | `prebuilt-utilityBill` | [link](2025-11-01/procurement/utilityBill.md) | [link](2026-06-01-preview/procurement/utilityBill.md) | Recurring service bill for utilities/metered or subscription services. |
| `creditMemo` | `prebuilt-creditMemo` | [link](2025-11-01/procurement/creditMemo.md) | [link](2026-06-01-preview/procurement/creditMemo.md) | Billing adjustment document (credit/debit memo, correction, refund) referencing a prior invoice. |
| `receipt.generic` | `prebuilt-receipt.generic` | [link](2025-11-01/procurement/receipt.generic.md) | [link](2026-06-01-preview/procurement/receipt.generic.md) | Point-of-sale or immediate-payment proof of purchase. |
| `receipt.hotel` | `prebuilt-receipt.hotel` | [link](2025-11-01/procurement/receipt.hotel.md) | [link](2026-06-01-preview/procurement/receipt.hotel.md) | Lodging folio or hotel stay statement. |

### Receipts

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `receipt` (index) | — | [link](2025-11-01/receipt/receipt.md) | [link](2026-06-01-preview/receipt/receipt.md) | Index of receipt document sub-types. |
| `receipt.generic` | `prebuilt-receipt.generic` | [link](2025-11-01/receipt/receipt.generic.md) | [link](2026-06-01-preview/receipt/receipt.generic.md) | Retail/restaurant or general POS transaction receipt. |
| `receipt.hotel` | `prebuilt-receipt.hotel` | [link](2025-11-01/receipt/receipt.hotel.md) | [link](2026-06-01-preview/receipt/receipt.hotel.md) | Hotel folio or lodging receipt. |

### Tax (US)

| Category | Analyzer ID | Schema (2025-11-01) | Schema (2026-06-01-preview) | Description |
|:---------|:------------|:---------------------|:------------------------------|:-------------|
| `tax.us` (index) | — | [link](2025-11-01/tax.us/tax.us.md) | [link](2026-06-01-preview/tax.us/tax.us.md) | Index of all U.S. federal tax form sub-types (1040 family, 1099 family, W-2, W-4, etc.). |
| `tax.us.mn.m1` (preview only) | `prebuilt-tax.us.mn.m1` | — | [link](2026-06-01-preview/tax.us.mn.m1/tax.us.mn.m1.md) | Minnesota state Form M1 (Individual Income Tax). |

Each entry in the `tax.us` index page links to its own schema file, for example [`tax.us.1040.md`](2025-11-01/tax.us/tax.us.1040.md) (Form 1040) or [`tax.us.w2.md`](2025-11-01/tax.us/tax.us.w2.md) (Form W-2). In `2026-06-01-preview`, each tax form additionally has its own folder with a non-versioned schema (e.g. [`tax.us.1040/tax.us.1040.md`](2026-06-01-preview/tax.us/tax.us.1040/tax.us.1040.md)) and a year-versioned schema (e.g. [`tax.us.1040/tax.us.1040.2025.md`](2026-06-01-preview/tax.us/tax.us.1040/tax.us.1040.2025.md), analyzer ID `prebuilt-tax.us.1040.2025`).
