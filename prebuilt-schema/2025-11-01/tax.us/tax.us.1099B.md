**Analyzer ID:** `prebuilt-tax.us.1099B`

**Description:** Proceeds from Broker and Barter Exchange Transactions.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099BCopies`|`array`|`generate`|Array of IRS Form 1099-B copy instances found in the document.||
|`Form1099BCopies.*`|`object`|`generate`|IRS Form 1099-B copy details.||
|`Form1099BCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-B.|2025|
|`Form1099BCopies.*.CopyLabel`|`string`|`extract`|Form 1099-B copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099BCopies.*.Payer`|`object`|`generate`|||
|`Form1099BCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099BCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099BCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099BCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099BCopies.*.Recipient`|`object`|`generate`|||
|`Form1099BCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|987-65-4321|
|`Form1099BCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099BCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099BCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099BCopies.*.Transactions`|`array`|`generate`|List of transactions reported in the Form 1099-B||
|`Form1099BCopies.*.Transactions.*`|`object`|`generate`|||
|`Form1099BCopies.*.Transactions.*.CUSIPNumber`|`string`|`extract`|CUSIP Number extracted from Form 1099-B.|0123456789|
|`Form1099BCopies.*.Transactions.*.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-B.|false|
|`Form1099BCopies.*.Transactions.*.ApplicableForm8949Checkbox`|`string`|`extract`|Applicable Form 8949 Checkbox extracted from Form 1099-B.|A|
|`Form1099BCopies.*.Transactions.*.Box1a`|`string`|`extract`|Box 1a extracted from Form 1099-B.|123 sh. MSFT|
|`Form1099BCopies.*.Transactions.*.Box1b`|`date`|`extract`|Box 1b extracted from Form 1099-B.|2025-01-01|
|`Form1099BCopies.*.Transactions.*.Box1c`|`date`|`extract`|Box 1c extracted from Form 1099-B.|2025-01-01|
|`Form1099BCopies.*.Transactions.*.Box1d`|`number`|`extract`|Box 1d extracted from Form 1099-B.|123456|
|`Form1099BCopies.*.Transactions.*.Box1e`|`number`|`extract`|Box 1e extracted from Form 1099-B.|98765|
|`Form1099BCopies.*.Transactions.*.Box1f`|`number`|`extract`|Box 1f extracted from Form 1099-B.|0|
|`Form1099BCopies.*.Transactions.*.Box1g`|`number`|`extract`|Box 1g extracted from Form 1099-B.|0|
|`Form1099BCopies.*.Transactions.*.Box2`|`array`|`generate`|Gain/loss term selection(s).||
|`Form1099BCopies.*.Transactions.*.Box2.*`|`string`|`extract`||longTermGainOrLoss|
|`Form1099BCopies.*.Transactions.*.Box3`|`array`|`generate`|Proceeds type selection(s).||
|`Form1099BCopies.*.Transactions.*.Box3.*`|`string`|`extract`||collectibles|
|`Form1099BCopies.*.Transactions.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-B.|12456|
|`Form1099BCopies.*.Transactions.*.Box5`|`boolean`|`extract`|Box 5 extracted from Form 1099-B.|true|
|`Form1099BCopies.*.Transactions.*.Box6`|`array`|`generate`|Reported to IRS selection(s).||
|`Form1099BCopies.*.Transactions.*.Box6.*`|`string`|`extract`||netProceeds|
|`Form1099BCopies.*.Transactions.*.Box7`|`boolean`|`extract`|Box 7 extracted from Form 1099-B.|false|
|`Form1099BCopies.*.Transactions.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-B.|654321|
|`Form1099BCopies.*.Transactions.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-B.|0|
|`Form1099BCopies.*.Transactions.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-B.|0|
|`Form1099BCopies.*.Transactions.*.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-B.|0|
|`Form1099BCopies.*.Transactions.*.Box12`|`boolean`|`extract`|Box 12 extracted from Form 1099-B.|false|
|`Form1099BCopies.*.Transactions.*.Box13`|`number`|`extract`|Box 13 extracted from Form 1099-B.|0|
|`Form1099BCopies.*.Transactions.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-B||
|`Form1099BCopies.*.Transactions.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099BCopies.*.Transactions.*.StateTaxesWithheld.*.Box14`|`string`|`extract`|Box 14 extracted from Form 1099-B.|WA|
|`Form1099BCopies.*.Transactions.*.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-B.|87654321|
|`Form1099BCopies.*.Transactions.*.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-B.|321|
|`Form1099BCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
