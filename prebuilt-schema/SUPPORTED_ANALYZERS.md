# Supported Domain-Specific Prebuilt Analyzers

Use this single-file index to select an Azure Content Understanding domain-specific prebuilt analyzer by API version, then follow its schema link to inspect the returned fields. Analyzer descriptions are sourced from the schema pages and the [official prebuilt analyzer documentation](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers#domain-specific-analyzers-in-detail).

## Selection guidance

1. Choose the API version first. `2025-11-01` is stable; `2026-06-01-preview` includes preview and year-versioned analyzers.
2. Prefer the most specific analyzer when the document type is known.
3. Use a composed family analyzer (`prebuilt-idDocument`, `prebuilt-mortgage.us`, `prebuilt-procurement`, `prebuilt-receipt`, or `prebuilt-tax.us`) when the family is known but the subtype is not.
4. If no domain-specific prebuilt analyzer fits, use a [utility analyzer](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers#utility-analyzers): `prebuilt-documentFields` to extract key-value pairs, or `prebuilt-documentFieldSchema` to propose a starting schema for a [custom analyzer](https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/create-custom-analyzer).

Each table contains one row per unique analyzer ID. Duplicate receipt IDs use canonical links to the `receipt/` schemas rather than the `/procurement/` copies.

## 2025-11-01

Stable, generally available API version.

| Analyzer ID | Description | Schema |
| --- | --- | --- |
| `prebuilt-bankStatement.us` | US bank statements. | [schema](2025-11-01/finance/bankStatement.us.md) |
| `prebuilt-check.us` | US bank checks. | [schema](2025-11-01/finance/check.us.md) |
| `prebuilt-contract` | Business contracts and agreements. | [schema](2025-11-01/legal/contract.md) |
| `prebuilt-creditCard` | Credit card statements. | [schema](2025-11-01/finance/creditCard.md) |
| `prebuilt-creditMemo` | Credit memos and refund documents. | [schema](2025-11-01/procurement/creditMemo.md) |
| `prebuilt-healthInsuranceCard.us` | US health insurance cards. | [schema](2025-11-01/personalRecords/healthInsuranceCard.us.md) |
| `prebuilt-idDocument` | A composed prebuilt analyzer for various ID documentation types. | [schema](2025-11-01/idDocument/idDocument.md) |
| `prebuilt-idDocument.generic` | Generic identification documents from various regions. | [schema](2025-11-01/idDocument/idDocument.generic.md) |
| `prebuilt-idDocument.passport` | Passport books and passport cards. | [schema](2025-11-01/idDocument/idDocument.passport.md) |
| `prebuilt-invoice` | Invoices, utility bills, sales orders, purchase orders. | [schema](2025-11-01/procurement/invoice.md) |
| `prebuilt-marriageCertificate.us` | US marriage certificates. | [schema](2025-11-01/personalRecords/marriageCertificate.us.md) |
| `prebuilt-mortgage.us` | A composed prebuilt analyzer that classifies and routes a mortgage document to the correct mortgage analyzer for extraction. | [schema](2025-11-01/mortgage.us/mortgage.us.md) |
| `prebuilt-mortgage.us.1003` | Uniform Residential Loan Application. | [schema](2025-11-01/mortgage.us/mortgage.us.1003.md) |
| `prebuilt-mortgage.us.1004` | Uniform Residential Appraisal Report. | [schema](2025-11-01/mortgage.us/mortgage.us.1004.md) |
| `prebuilt-mortgage.us.1005` | Verification of Employment. | [schema](2025-11-01/mortgage.us/mortgage.us.1005.md) |
| `prebuilt-mortgage.us.1008` | Uniform Underwriting and Transmittal Summary. | [schema](2025-11-01/mortgage.us/mortgage.us.1008.md) |
| `prebuilt-mortgage.us.closingDisclosure` | Closing Disclosure. | [schema](2025-11-01/mortgage.us/mortgage.us.closingDisclosure.md) |
| `prebuilt-payStub.us` | US pay stubs and earnings statements. | [schema](2025-11-01/finance/payStub.us.md) |
| `prebuilt-procurement` | A composed prebuilt analyzer that classifies and routes a procurement document to the correct procurement analyzer for extraction. | [schema](2025-11-01/procurement/procurement.md) |
| `prebuilt-purchaseOrder` | Purchase order forms. | [schema](2025-11-01/procurement/purchaseOrder.md) |
| `prebuilt-receipt` | A composed prebuilt analyzer for sales receipts. | [schema](2025-11-01/receipt/receipt.md) |
| `prebuilt-receipt.generic` | General sales receipts. | [schema](2025-11-01/receipt/receipt.generic.md) |
| `prebuilt-receipt.hotel` | Hotel receipts and folios. | [schema](2025-11-01/receipt/receipt.hotel.md) |
| `prebuilt-tax.us` | A composed prebuilt analyzer that classifies and routes a US tax form to the correct tax analyzer for extraction. | [schema](2025-11-01/tax.us/tax.us.md) |
| `prebuilt-tax.us.1040` | Form 1040 (US Individual Income Tax Return). | [schema](2025-11-01/tax.us/tax.us.1040.md) |
| `prebuilt-tax.us.1040Schedule1` | Additional Income and Adjustments to Income. | [schema](2025-11-01/tax.us/tax.us.1040Schedule1.md) |
| `prebuilt-tax.us.1040Schedule2` | Additional Taxes. | [schema](2025-11-01/tax.us/tax.us.1040Schedule2.md) |
| `prebuilt-tax.us.1040Schedule3` | Additional Credits and Payments. | [schema](2025-11-01/tax.us/tax.us.1040Schedule3.md) |
| `prebuilt-tax.us.1040Schedule8812` | Credits for Qualifying Children. | [schema](2025-11-01/tax.us/tax.us.1040Schedule8812.md) |
| `prebuilt-tax.us.1040ScheduleA` | Itemized Deductions. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleA.md) |
| `prebuilt-tax.us.1040ScheduleB` | Interest and Ordinary Dividends. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleB.md) |
| `prebuilt-tax.us.1040ScheduleC` | Profit or Loss from Business. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleC.md) |
| `prebuilt-tax.us.1040ScheduleD` | Capital Gains and Losses. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleD.md) |
| `prebuilt-tax.us.1040ScheduleE` | Supplemental Income and Loss. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleE.md) |
| `prebuilt-tax.us.1040ScheduleEIC` | Earned Income Credit. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleEIC.md) |
| `prebuilt-tax.us.1040ScheduleF` | Profit or Loss from Farming. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleF.md) |
| `prebuilt-tax.us.1040ScheduleH` | Household Employment Taxes. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleH.md) |
| `prebuilt-tax.us.1040ScheduleJ` | Income Averaging for Farmers. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleJ.md) |
| `prebuilt-tax.us.1040ScheduleR` | Credit for the Elderly or Disabled. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleR.md) |
| `prebuilt-tax.us.1040ScheduleSE` | Self-Employment Tax. | [schema](2025-11-01/tax.us/tax.us.1040ScheduleSE.md) |
| `prebuilt-tax.us.1040Senior` | Form 1040 for senior taxpayers. | [schema](2025-11-01/tax.us/tax.us.1040Senior.md) |
| `prebuilt-tax.us.1095A` | Health Insurance Marketplace Statement. | [schema](2025-11-01/tax.us/tax.us.1095A.md) |
| `prebuilt-tax.us.1095C` | Employer-Provided Health Insurance. | [schema](2025-11-01/tax.us/tax.us.1095C.md) |
| `prebuilt-tax.us.1098` | Mortgage Interest Statement. | [schema](2025-11-01/tax.us/tax.us.1098.md) |
| `prebuilt-tax.us.1098E` | Student Loan Interest Statement. | [schema](2025-11-01/tax.us/tax.us.1098E.md) |
| `prebuilt-tax.us.1098T` | Tuition Statement. | [schema](2025-11-01/tax.us/tax.us.1098T.md) |
| `prebuilt-tax.us.1099A` | Acquisition or Abandonment of Secured Property. | [schema](2025-11-01/tax.us/tax.us.1099A.md) |
| `prebuilt-tax.us.1099B` | Proceeds from Broker and Barter Exchange Transactions. | [schema](2025-11-01/tax.us/tax.us.1099B.md) |
| `prebuilt-tax.us.1099C` | Cancellation of Debt. | [schema](2025-11-01/tax.us/tax.us.1099C.md) |
| `prebuilt-tax.us.1099CAP` | Changes in Corporate Control and Capital Structure. | [schema](2025-11-01/tax.us/tax.us.1099CAP.md) |
| `prebuilt-tax.us.1099Combo` | Combined 1099 forms. | [schema](2025-11-01/tax.us/tax.us.1099Combo.md) |
| `prebuilt-tax.us.1099DA` | Debt Cancellation from Foreclosure. | [schema](2025-11-01/tax.us/tax.us.1099DA.md) |
| `prebuilt-tax.us.1099DIV` | Dividends and Distributions. | [schema](2025-11-01/tax.us/tax.us.1099DIV.md) |
| `prebuilt-tax.us.1099G` | Certain Government Payments. | [schema](2025-11-01/tax.us/tax.us.1099G.md) |
| `prebuilt-tax.us.1099H` | Health Coverage Tax Credit Advance Payments. | [schema](2025-11-01/tax.us/tax.us.1099H.md) |
| `prebuilt-tax.us.1099INT` | Interest Income. | [schema](2025-11-01/tax.us/tax.us.1099INT.md) |
| `prebuilt-tax.us.1099K` | Payment Card and Third Party Network Transactions. | [schema](2025-11-01/tax.us/tax.us.1099K.md) |
| `prebuilt-tax.us.1099LS` | Reportable Life Insurance Sale. | [schema](2025-11-01/tax.us/tax.us.1099LS.md) |
| `prebuilt-tax.us.1099LTC` | Long-Term Care Benefits. | [schema](2025-11-01/tax.us/tax.us.1099LTC.md) |
| `prebuilt-tax.us.1099MISC` | Miscellaneous Income. | [schema](2025-11-01/tax.us/tax.us.1099MISC.md) |
| `prebuilt-tax.us.1099NEC` | Nonemployee Compensation. | [schema](2025-11-01/tax.us/tax.us.1099NEC.md) |
| `prebuilt-tax.us.1099OID` | Original Issue Discount. | [schema](2025-11-01/tax.us/tax.us.1099OID.md) |
| `prebuilt-tax.us.1099PATR` | Taxable Distributions from Cooperatives. | [schema](2025-11-01/tax.us/tax.us.1099PATR.md) |
| `prebuilt-tax.us.1099Q` | Payments from Qualified Education Programs. | [schema](2025-11-01/tax.us/tax.us.1099Q.md) |
| `prebuilt-tax.us.1099QA` | Distributions from ABLE Accounts. | [schema](2025-11-01/tax.us/tax.us.1099QA.md) |
| `prebuilt-tax.us.1099R` | Distributions from Pensions and Annuities. | [schema](2025-11-01/tax.us/tax.us.1099R.md) |
| `prebuilt-tax.us.1099S` | Proceeds from Real Estate Transactions. | [schema](2025-11-01/tax.us/tax.us.1099S.md) |
| `prebuilt-tax.us.1099SA` | Distributions from Health Savings Account (HSA) or Medical Savings Account (MSA). | [schema](2025-11-01/tax.us/tax.us.1099SA.md) |
| `prebuilt-tax.us.1099SB` | Seller's Investment in Life Insurance Contract. | [schema](2025-11-01/tax.us/tax.us.1099SB.md) |
| `prebuilt-tax.us.1099SSA` | Social Security Benefit Statement. | [schema](2025-11-01/tax.us/tax.us.1099SSA.md) |
| `prebuilt-tax.us.w2` | Wage and Tax Statement. | [schema](2025-11-01/tax.us/tax.us.w2.md) |
| `prebuilt-tax.us.w4` | Employee's Withholding Certificate. | [schema](2025-11-01/tax.us/tax.us.w4.md) |
| `prebuilt-utilityBill` | Utility bills (electricity, water, gas, internet, phone). | [schema](2025-11-01/procurement/utilityBill.md) |

## 2026-06-01-preview

Preview API version.

| Analyzer ID | Description | Schema |
| --- | --- | --- |
| `prebuilt-bankStatement.us` | US bank statements. | [schema](2026-06-01-preview/finance/bankStatement.us.md) |
| `prebuilt-check.us` | US bank checks. | [schema](2026-06-01-preview/finance/check.us.md) |
| `prebuilt-contract` | Business contracts and agreements. | [schema](2026-06-01-preview/legal/contract.md) |
| `prebuilt-creditCard` | Credit card statements. | [schema](2026-06-01-preview/finance/creditCard.md) |
| `prebuilt-creditMemo` | Credit memos and refund documents. | [schema](2026-06-01-preview/procurement/creditMemo.md) |
| `prebuilt-healthInsuranceCard.us` | US health insurance cards. | [schema](2026-06-01-preview/personalRecords/healthInsuranceCard.us.md) |
| `prebuilt-idDocument` | A composed prebuilt analyzer for various ID documentation types. | [schema](2026-06-01-preview/idDocument/idDocument.md) |
| `prebuilt-idDocument.generic` | Generic identification documents from various regions. | [schema](2026-06-01-preview/idDocument/idDocument.generic.md) |
| `prebuilt-idDocument.passport` | Passport books and passport cards (worldwide). | [schema](2026-06-01-preview/idDocument/idDocument.passport.md) |
| `prebuilt-invoice` | Invoices, utility bills, sales orders, purchase orders. | [schema](2026-06-01-preview/procurement/invoice.md) |
| `prebuilt-marriageCertificate.us` | US marriage certificates. | [schema](2026-06-01-preview/personalRecords/marriageCertificate.us.md) |
| `prebuilt-mortgage.us` | A composed prebuilt analyzer that classifies and routes a mortgage document to the correct mortgage analyzer for extraction. | [schema](2026-06-01-preview/mortgage.us/mortgage.us.md) |
| `prebuilt-mortgage.us.1003` | Uniform Residential Loan Application. | [schema](2026-06-01-preview/mortgage.us/mortgage.us.1003.md) |
| `prebuilt-mortgage.us.1004` | Uniform Residential Appraisal Report. | [schema](2026-06-01-preview/mortgage.us/mortgage.us.1004.md) |
| `prebuilt-mortgage.us.1005` | Verification of Employment. | [schema](2026-06-01-preview/mortgage.us/mortgage.us.1005.md) |
| `prebuilt-mortgage.us.1008` | Uniform Underwriting and Transmittal Summary. | [schema](2026-06-01-preview/mortgage.us/mortgage.us.1008.md) |
| `prebuilt-mortgage.us.closingDisclosure` | Closing Disclosure. | [schema](2026-06-01-preview/mortgage.us/mortgage.us.closingDisclosure.md) |
| `prebuilt-payStub.us` | US pay stubs and earnings statements. | [schema](2026-06-01-preview/finance/payStub.us.md) |
| `prebuilt-procurement` | A composed prebuilt analyzer that classifies and routes a procurement document to the correct procurement analyzer for extraction. | [schema](2026-06-01-preview/procurement/procurement.md) |
| `prebuilt-purchaseOrder` | Purchase order forms. | [schema](2026-06-01-preview/procurement/purchaseOrder.md) |
| `prebuilt-receipt` | A composed prebuilt analyzer for sales receipts. | [schema](2026-06-01-preview/receipt/receipt.md) |
| `prebuilt-receipt.generic` | General sales receipts. | [schema](2026-06-01-preview/receipt/receipt.generic.md) |
| `prebuilt-receipt.hotel` | Hotel receipts and folios. | [schema](2026-06-01-preview/receipt/receipt.hotel.md) |
| `prebuilt-tax.us` | A composed prebuilt analyzer that classifies and routes a US tax form to the correct tax analyzer for extraction. | [schema](2026-06-01-preview/tax.us/tax.us.md) |
| `prebuilt-tax.us.1040` | Form 1040 (US Individual Income Tax Return). | [schema](2026-06-01-preview/tax.us/tax.us.1040/tax.us.1040.md) |
| `prebuilt-tax.us.1040.2025` | Extract tax US 1040 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040/tax.us.1040.2025.md) |
| `prebuilt-tax.us.1040Schedule1` | Additional Income and Adjustments to Income. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule1/tax.us.1040Schedule1.md) |
| `prebuilt-tax.us.1040Schedule1.2025` | Extract tax US 1040 schedule1 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule1/tax.us.1040Schedule1.2025.md) |
| `prebuilt-tax.us.1040Schedule2` | Additional Taxes. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule2/tax.us.1040Schedule2.md) |
| `prebuilt-tax.us.1040Schedule2.2025` | Extract tax US 1040 schedule2 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule2/tax.us.1040Schedule2.2025.md) |
| `prebuilt-tax.us.1040Schedule3` | Additional Credits and Payments. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule3/tax.us.1040Schedule3.md) |
| `prebuilt-tax.us.1040Schedule3.2025` | Extract tax US 1040 schedule3 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule3/tax.us.1040Schedule3.2025.md) |
| `prebuilt-tax.us.1040Schedule8812` | Credits for Qualifying Children. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule8812/tax.us.1040Schedule8812.md) |
| `prebuilt-tax.us.1040Schedule8812.2025` | Extract tax US 1040 schedule8812 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040Schedule8812/tax.us.1040Schedule8812.2025.md) |
| `prebuilt-tax.us.1040ScheduleA` | Itemized Deductions. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleA/tax.us.1040ScheduleA.md) |
| `prebuilt-tax.us.1040ScheduleA.2025` | Extract tax US 1040 schedule a document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleA/tax.us.1040ScheduleA.2025.md) |
| `prebuilt-tax.us.1040ScheduleB` | Interest and Ordinary Dividends. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleB/tax.us.1040ScheduleB.md) |
| `prebuilt-tax.us.1040ScheduleB.2025` | Extract tax US 1040 schedule b document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleB/tax.us.1040ScheduleB.2025.md) |
| `prebuilt-tax.us.1040ScheduleC` | Profit or Loss from Business. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleC/tax.us.1040ScheduleC.md) |
| `prebuilt-tax.us.1040ScheduleC.2025` | Extract tax US 1040 schedule c document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleC/tax.us.1040ScheduleC.2025.md) |
| `prebuilt-tax.us.1040ScheduleD` | Capital Gains and Losses. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleD/tax.us.1040ScheduleD.md) |
| `prebuilt-tax.us.1040ScheduleD.2025` | Extract tax US 1040 schedule d document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleD/tax.us.1040ScheduleD.2025.md) |
| `prebuilt-tax.us.1040ScheduleE` | Supplemental Income and Loss. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleE/tax.us.1040ScheduleE.md) |
| `prebuilt-tax.us.1040ScheduleE.2025` | Extract tax US 1040 schedule e document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleE/tax.us.1040ScheduleE.2025.md) |
| `prebuilt-tax.us.1040ScheduleEIC` | Earned Income Credit. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleEIC/tax.us.1040ScheduleEIC.md) |
| `prebuilt-tax.us.1040ScheduleEIC.2025` | Extract tax US 1040 schedule eic document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleEIC/tax.us.1040ScheduleEIC.2025.md) |
| `prebuilt-tax.us.1040ScheduleF` | Profit or Loss from Farming. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleF/tax.us.1040ScheduleF.md) |
| `prebuilt-tax.us.1040ScheduleF.2025` | Extract tax US 1040 schedule f document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleF/tax.us.1040ScheduleF.2025.md) |
| `prebuilt-tax.us.1040ScheduleH` | Household Employment Taxes. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleH/tax.us.1040ScheduleH.md) |
| `prebuilt-tax.us.1040ScheduleH.2025` | Extract tax US 1040 schedule h document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleH/tax.us.1040ScheduleH.2025.md) |
| `prebuilt-tax.us.1040ScheduleJ` | Income Averaging for Farmers. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleJ/tax.us.1040ScheduleJ.md) |
| `prebuilt-tax.us.1040ScheduleJ.2025` | Extract tax US 1040 schedule j document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleJ/tax.us.1040ScheduleJ.2025.md) |
| `prebuilt-tax.us.1040ScheduleR` | Credit for the Elderly or Disabled. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleR/tax.us.1040ScheduleR.md) |
| `prebuilt-tax.us.1040ScheduleR.2025` | Extract tax US 1040 schedule r document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleR/tax.us.1040ScheduleR.2025.md) |
| `prebuilt-tax.us.1040ScheduleSE` | Self-Employment Tax. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleSE/tax.us.1040ScheduleSE.md) |
| `prebuilt-tax.us.1040ScheduleSE.2025` | Extract tax US 1040 schedule se document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040ScheduleSE/tax.us.1040ScheduleSE.2025.md) |
| `prebuilt-tax.us.1040Senior` | Form 1040 for senior taxpayers. | [schema](2026-06-01-preview/tax.us/tax.us.1040Senior/tax.us.1040Senior.md) |
| `prebuilt-tax.us.1040Senior.2025` | Extract tax US 1040 senior document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1040Senior/tax.us.1040Senior.2025.md) |
| `prebuilt-tax.us.1041ScheduleK1` | Estate and Trust Schedule K-1 (Form 1041). | [schema](2026-06-01-preview/tax.us/tax.us.1041ScheduleK1/tax.us.1041ScheduleK1.md) |
| `prebuilt-tax.us.1041ScheduleK1.2025` | Extract tax US 1041 Schedule K-1 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1041ScheduleK1/tax.us.1041ScheduleK1.2025.md) |
| `prebuilt-tax.us.1065ScheduleK1` | Partnership Schedule K-1 (Form 1065). | [schema](2026-06-01-preview/tax.us/tax.us.1065ScheduleK1/tax.us.1065ScheduleK1.md) |
| `prebuilt-tax.us.1065ScheduleK1.2025` | Extract tax US 1065 Schedule K-1 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1065ScheduleK1/tax.us.1065ScheduleK1.2025.md) |
| `prebuilt-tax.us.1095A` | Health Insurance Marketplace Statement. | [schema](2026-06-01-preview/tax.us/tax.us.1095A/tax.us.1095A.md) |
| `prebuilt-tax.us.1095A.2025` | Extract tax US 1095 a document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1095A/tax.us.1095A.2025.md) |
| `prebuilt-tax.us.1095C` | Employer-Provided Health Insurance. | [schema](2026-06-01-preview/tax.us/tax.us.1095C/tax.us.1095C.md) |
| `prebuilt-tax.us.1095C.2025` | Extract tax US 1095 c document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1095C/tax.us.1095C.2025.md) |
| `prebuilt-tax.us.1098` | Mortgage Interest Statement. | [schema](2026-06-01-preview/tax.us/tax.us.1098/tax.us.1098.md) |
| `prebuilt-tax.us.1098.2025` | Extract tax US 1098 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1098/tax.us.1098.2025.md) |
| `prebuilt-tax.us.1098E` | Student Loan Interest Statement. | [schema](2026-06-01-preview/tax.us/tax.us.1098E/tax.us.1098E.md) |
| `prebuilt-tax.us.1098E.2025` | Extract tax US 1098 e document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1098E/tax.us.1098E.2025.md) |
| `prebuilt-tax.us.1098T` | Tuition Statement. | [schema](2026-06-01-preview/tax.us/tax.us.1098T/tax.us.1098T.md) |
| `prebuilt-tax.us.1098T.2025` | Extract tax US 1098 t document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1098T/tax.us.1098T.2025.md) |
| `prebuilt-tax.us.1099A` | Acquisition or Abandonment of Secured Property. | [schema](2026-06-01-preview/tax.us/tax.us.1099A/tax.us.1099A.md) |
| `prebuilt-tax.us.1099A.2025` | Extract tax US 1099 a document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099A/tax.us.1099A.2025.md) |
| `prebuilt-tax.us.1099B` | Proceeds from Broker and Barter Exchange Transactions. | [schema](2026-06-01-preview/tax.us/tax.us.1099B/tax.us.1099B.md) |
| `prebuilt-tax.us.1099B.2025` | Extract tax US 1099 b document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099B/tax.us.1099B.2025.md) |
| `prebuilt-tax.us.1099C` | Cancellation of Debt. | [schema](2026-06-01-preview/tax.us/tax.us.1099C/tax.us.1099C.md) |
| `prebuilt-tax.us.1099C.2025` | Extract tax US 1099 c document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099C/tax.us.1099C.2025.md) |
| `prebuilt-tax.us.1099CAP` | Changes in Corporate Control and Capital Structure. | [schema](2026-06-01-preview/tax.us/tax.us.1099CAP/tax.us.1099CAP.md) |
| `prebuilt-tax.us.1099CAP.2025` | Extract tax US 1099 cap document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099CAP/tax.us.1099CAP.2025.md) |
| `prebuilt-tax.us.1099Combo` | Combined 1099 forms. | [schema](2026-06-01-preview/tax.us/tax.us.1099Combo/tax.us.1099Combo.md) |
| `prebuilt-tax.us.1099Combo.2025` | Extract tax US 1099 combo document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099Combo/tax.us.1099Combo.2025.md) |
| `prebuilt-tax.us.1099DA` | Debt Cancellation from Foreclosure. | [schema](2026-06-01-preview/tax.us/tax.us.1099DA/tax.us.1099DA.md) |
| `prebuilt-tax.us.1099DA.2025` | Extract tax US 1099 da document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099DA/tax.us.1099DA.2025.md) |
| `prebuilt-tax.us.1099DIV` | Dividends and Distributions. | [schema](2026-06-01-preview/tax.us/tax.us.1099DIV/tax.us.1099DIV.md) |
| `prebuilt-tax.us.1099DIV.2025` | Extract tax US 1099 div document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099DIV/tax.us.1099DIV.2025.md) |
| `prebuilt-tax.us.1099G` | Certain Government Payments. | [schema](2026-06-01-preview/tax.us/tax.us.1099G/tax.us.1099G.md) |
| `prebuilt-tax.us.1099G.2025` | Extract tax US 1099 g document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099G/tax.us.1099G.2025.md) |
| `prebuilt-tax.us.1099H` | Health Coverage Tax Credit Advance Payments. | [schema](2026-06-01-preview/tax.us/tax.us.1099H/tax.us.1099H.md) |
| `prebuilt-tax.us.1099H.2025` | Extract tax US 1099 h document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099H/tax.us.1099H.2025.md) |
| `prebuilt-tax.us.1099INT` | Interest Income. | [schema](2026-06-01-preview/tax.us/tax.us.1099INT/tax.us.1099INT.md) |
| `prebuilt-tax.us.1099INT.2025` | Extract tax US 1099 int document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099INT/tax.us.1099INT.2025.md) |
| `prebuilt-tax.us.1099K` | Payment Card and Third Party Network Transactions. | [schema](2026-06-01-preview/tax.us/tax.us.1099K/tax.us.1099K.md) |
| `prebuilt-tax.us.1099K.2025` | Extract tax US 1099 k document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099K/tax.us.1099K.2025.md) |
| `prebuilt-tax.us.1099LS` | Reportable Life Insurance Sale. | [schema](2026-06-01-preview/tax.us/tax.us.1099LS/tax.us.1099LS.md) |
| `prebuilt-tax.us.1099LS.2025` | Extract tax US 1099 ls document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099LS/tax.us.1099LS.2025.md) |
| `prebuilt-tax.us.1099LTC` | Long-Term Care Benefits. | [schema](2026-06-01-preview/tax.us/tax.us.1099LTC/tax.us.1099LTC.md) |
| `prebuilt-tax.us.1099LTC.2025` | Extract tax US 1099 ltc document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099LTC/tax.us.1099LTC.2025.md) |
| `prebuilt-tax.us.1099MISC` | Miscellaneous Income. | [schema](2026-06-01-preview/tax.us/tax.us.1099MISC/tax.us.1099MISC.md) |
| `prebuilt-tax.us.1099MISC.2025` | Extract tax US 1099 misc document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099MISC/tax.us.1099MISC.2025.md) |
| `prebuilt-tax.us.1099NEC` | Nonemployee Compensation. | [schema](2026-06-01-preview/tax.us/tax.us.1099NEC/tax.us.1099NEC.md) |
| `prebuilt-tax.us.1099NEC.2025` | Extract tax US 1099 nec document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099NEC/tax.us.1099NEC.2025.md) |
| `prebuilt-tax.us.1099OID` | Original Issue Discount. | [schema](2026-06-01-preview/tax.us/tax.us.1099OID/tax.us.1099OID.md) |
| `prebuilt-tax.us.1099OID.2025` | Extract tax US 1099 oid document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099OID/tax.us.1099OID.2025.md) |
| `prebuilt-tax.us.1099PATR` | Taxable Distributions from Cooperatives. | [schema](2026-06-01-preview/tax.us/tax.us.1099PATR/tax.us.1099PATR.md) |
| `prebuilt-tax.us.1099PATR.2025` | Extract tax US 1099 patr document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099PATR/tax.us.1099PATR.2025.md) |
| `prebuilt-tax.us.1099Q` | Payments from Qualified Education Programs. | [schema](2026-06-01-preview/tax.us/tax.us.1099Q/tax.us.1099Q.md) |
| `prebuilt-tax.us.1099Q.2025` | Extract tax US 1099 q document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099Q/tax.us.1099Q.2025.md) |
| `prebuilt-tax.us.1099QA` | Distributions from ABLE Accounts. | [schema](2026-06-01-preview/tax.us/tax.us.1099QA/tax.us.1099QA.md) |
| `prebuilt-tax.us.1099QA.2025` | Extract tax US 1099 qa document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099QA/tax.us.1099QA.2025.md) |
| `prebuilt-tax.us.1099R` | Distributions from Pensions and Annuities. | [schema](2026-06-01-preview/tax.us/tax.us.1099R/tax.us.1099R.md) |
| `prebuilt-tax.us.1099R.2025` | Extract tax US 1099 r document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099R/tax.us.1099R.2025.md) |
| `prebuilt-tax.us.1099S` | Proceeds from Real Estate Transactions. | [schema](2026-06-01-preview/tax.us/tax.us.1099S/tax.us.1099S.md) |
| `prebuilt-tax.us.1099S.2025` | Extract tax US 1099 s document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099S/tax.us.1099S.2025.md) |
| `prebuilt-tax.us.1099SA` | Distributions from Health Savings Account (HSA) or Medical Savings Account (MSA). | [schema](2026-06-01-preview/tax.us/tax.us.1099SA/tax.us.1099SA.md) |
| `prebuilt-tax.us.1099SA.2025` | Extract tax US 1099 sa document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099SA/tax.us.1099SA.2025.md) |
| `prebuilt-tax.us.1099SB` | Seller's Investment in Life Insurance Contract. | [schema](2026-06-01-preview/tax.us/tax.us.1099SB/tax.us.1099SB.md) |
| `prebuilt-tax.us.1099SB.2025` | Extract tax US 1099 sb document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099SB/tax.us.1099SB.2025.md) |
| `prebuilt-tax.us.1099SSA` | Social Security Benefit Statement. | [schema](2026-06-01-preview/tax.us/tax.us.1099SSA/tax.us.1099SSA.md) |
| `prebuilt-tax.us.1099SSA.2025` | Extract tax US 1099 ssa document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1099SSA/tax.us.1099SSA.2025.md) |
| `prebuilt-tax.us.1120SScheduleK1` | S-Corporation Schedule K-1 (Form 1120-S). | [schema](2026-06-01-preview/tax.us/tax.us.1120SScheduleK1/tax.us.1120SScheduleK1.md) |
| `prebuilt-tax.us.1120SScheduleK1.2025` | Extract tax US 1120-S Schedule K-1 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.1120SScheduleK1/tax.us.1120SScheduleK1.2025.md) |
| `prebuilt-tax.us.8865ScheduleK1` | Foreign Partnership Schedule K-1 (Form 8865). | [schema](2026-06-01-preview/tax.us/tax.us.8865ScheduleK1/tax.us.8865ScheduleK1.md) |
| `prebuilt-tax.us.8865ScheduleK1.2025` | Extract tax US 8865 Schedule K-1 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.8865ScheduleK1/tax.us.8865ScheduleK1.2025.md) |
| `prebuilt-tax.us.mn.m1` | Minnesota Form M1 — Individual Income Tax Return. | [schema](2026-06-01-preview/tax.us.mn.m1/tax.us.mn.m1.md) |
| `prebuilt-tax.us.mn.m1.2025` | Extract tax US Minnesota M1 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us.mn.m1/tax.us.mn.m1.2025.md) |
| `prebuilt-tax.us.w2` | Wage and Tax Statement. | [schema](2026-06-01-preview/tax.us/tax.us.w2/tax.us.w2.md) |
| `prebuilt-tax.us.w2.2025` | Extract tax US w2 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.w2/tax.us.w2.2025.md) |
| `prebuilt-tax.us.w4` | Employee's Withholding Certificate. | [schema](2026-06-01-preview/tax.us/tax.us.w4/tax.us.w4.md) |
| `prebuilt-tax.us.w4.2025` | Extract tax US w4 document fields of 2025 form. | [schema](2026-06-01-preview/tax.us/tax.us.w4/tax.us.w4.2025.md) |
| `prebuilt-utilityBill` | Utility bills (electricity, water, gas, internet, phone). | [schema](2026-06-01-preview/procurement/utilityBill.md) |
