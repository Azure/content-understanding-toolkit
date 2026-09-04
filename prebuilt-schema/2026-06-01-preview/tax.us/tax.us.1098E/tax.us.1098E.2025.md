**Analyzer ID:** `prebuilt-tax.us.1098E.2025`

**Description:** Extract tax US 1098 e document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1098ECopies`|`array`|`generate`|Array of IRS Form 1098-E copy instances found in the document.||
|`Form1098ECopies.*`|`object`|`generate`|IRS Form 1098-E copy details.||
|`Form1098ECopies.*.TaxYear`|`string`|`extract`|Form tax year|2021|
|`Form1098ECopies.*.CopyLabel`|`string`|`extract`|Form 1098-E copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1098ECopies.*.Borrower`|`object`|`generate`|||
|`Form1098ECopies.*.Borrower.TIN`|`string`|`extract`|Borrower's tax identification number|987-65-4321|
|`Form1098ECopies.*.Borrower.Name`|`string`|`extract`|Borrower's full name as written on the form|John Smith|
|`Form1098ECopies.*.Borrower.Address`|`string`|`extract`|Borrower's address|123 Microsoft Way, Redmond WA 98052|
|`Form1098ECopies.*.Borrower.AccountNumber`|`string`|`extract`|Borrower's account number|55123456789|
|`Form1098ECopies.*.Lender`|`object`|`generate`|||
|`Form1098ECopies.*.Lender.TIN`|`string`|`extract`|Lender's tax identification number|12-3456789|
|`Form1098ECopies.*.Lender.Name`|`string`|`extract`|Lender's name|Woodgrove Bank|
|`Form1098ECopies.*.Lender.Address`|`string`|`extract`|Lender's address|321 Microsoft Way, Redmond WA 98052|
|`Form1098ECopies.*.Lender.PhoneNumber`|`string`|`extract`|Lender's phone number|800-123-4567|
|`Form1098ECopies.*.StudentLoanInterest`|`number`|`extract`|Student loan interest received by lender (box 1)|5432.10|
|`Form1098ECopies.*.IsExcludingOriginationFeesOrCapitalizedInterest`|`boolean`|`extract`|Indicates box 1 excludes loan origination fees and/or capitalized interest for loans made before September 1, 2004 (box 2)|true|
|`Form1098ECopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrected filing|false|
