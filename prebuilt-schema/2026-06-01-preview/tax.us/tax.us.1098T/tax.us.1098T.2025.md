**Analyzer ID:** `prebuilt-tax.us.1098T.2025`

**Description:** Extract tax US 1098 t document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1098TCopies`|`array`|`generate`|Array of IRS Form 1098-T copy instances found in the document.||
|`Form1098TCopies.*`|`object`|`generate`|IRS Form 1098-T copy details.||
|`Form1098TCopies.*.TaxYear`|`string`|`extract`|Form tax year|2021|
|`Form1098TCopies.*.CopyLabel`|`string`|`extract`|Form 1098-T copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1098TCopies.*.Student`|`object`|`generate`|||
|`Form1098TCopies.*.Student.TIN`|`string`|`extract`|Student's tax identification number|123-45-6789|
|`Form1098TCopies.*.Student.Name`|`string`|`extract`|Student's full name as written on the form|John Smith|
|`Form1098TCopies.*.Student.Address`|`string`|`extract`|Student's address|123 Microsoft Way, Redmond WA 98052|
|`Form1098TCopies.*.Student.AccountNumber`|`string`|`extract`|Student's account number|55123456789|
|`Form1098TCopies.*.Filer`|`object`|`generate`|||
|`Form1098TCopies.*.Filer.TIN`|`string`|`extract`|Filer's tax identification number|12-3456789|
|`Form1098TCopies.*.Filer.Name`|`string`|`extract`|Filer's name|School of Fine Art|
|`Form1098TCopies.*.Filer.Address`|`string`|`extract`|Filer's address|PO Box 1234, Redmond WA 98052|
|`Form1098TCopies.*.Filer.PhoneNumber`|`string`|`extract`|Filer's phone number|800-123-4567|
|`Form1098TCopies.*.PaymentReceived`|`number`|`extract`|Payments received for qualified tuition and related expenses (box 1)|17123.98|
|`Form1098TCopies.*.AdjustmentsForPriorYear`|`number`|`extract`|Adjustments of payments for a prior year (box 4)|567.12|
|`Form1098TCopies.*.Scholarships`|`number`|`extract`|Scholarships or grants (box 5)|34567.89|
|`Form1098TCopies.*.ScholarshipsAdjustments`|`number`|`extract`|Adjustments of scholarships or grants for a prior year (box 6)|654.32|
|`Form1098TCopies.*.IsAmountForNextPeriodIncluded`|`boolean`|`extract`|Indicates the amount in box 1 includes amounts for an academic period beginning January–March of the next tax year (box 7)|false|
|`Form1098TCopies.*.IsAtLeastHalfTimeStudent`|`boolean`|`extract`|Indicates the student was at least a half-time student during any academic period in this tax year (box 8)|true|
|`Form1098TCopies.*.IsGraduateStudent`|`boolean`|`extract`|Indicates the student was a graduate student (box 9)|false|
|`Form1098TCopies.*.InsuranceContractReimbursements`|`number`|`extract`|Total amount of reimbursements or refunds of qualified tuition and related expenses (box 10)|321.67|
|`Form1098TCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrected filing|false|
