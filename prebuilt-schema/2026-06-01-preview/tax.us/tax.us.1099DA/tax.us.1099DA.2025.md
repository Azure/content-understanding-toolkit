**Analyzer ID:** `prebuilt-tax.us.1099DA.2025`

**Description:** Extract tax US 1099 da document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099DACopies`|`array`|`generate`|Array of IRS Form 1099-DA copy instances found in the document.||
|`Form1099DACopies.*`|`object`|`generate`|IRS Form 1099-DA copy details.||
|`Form1099DACopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-DA.|2025|
|`Form1099DACopies.*.CopyLabel`|`string`|`extract`|Form 1099-DA copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099DACopies.*.Filer`|`object`|`generate`|||
|`Form1099DACopies.*.Filer.TIN`|`string`|`extract`|Filer tax identification number.||
|`Form1099DACopies.*.Filer.Name`|`string`|`extract`|Filer full name as written on the form.||
|`Form1099DACopies.*.Filer.Address`|`string`|`extract`|Filer address.||
|`Form1099DACopies.*.Filer.PhoneNumber`|`string`|`extract`|Filer phone number.||
|`Form1099DACopies.*.Recipient`|`object`|`generate`|||
|`Form1099DACopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.||
|`Form1099DACopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.||
|`Form1099DACopies.*.Recipient.Address`|`string`|`extract`|Recipient address.||
|`Form1099DACopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.||
|`Form1099DACopies.*.Transactions`|`array`|`generate`|List of transactions reported in the Form 1099-DA||
|`Form1099DACopies.*.Transactions.*`|`object`|`generate`|||
|`Form1099DACopies.*.Transactions.*.CUSIPNumber`|`string`|`extract`|Cusip Number extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.ApplicableForm8949Checkbox`|`string`|`extract`|Applicable Form8949 Checkbox extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1a`|`string`|`extract`|Box 1a extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1b`|`string`|`extract`|Box 1b extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1c`|`number`|`extract`|Box 1c extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1d`|`date`|`extract`|Box 1d extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1e`|`date`|`extract`|Box 1e extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1f`|`number`|`extract`|Box 1f extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1g`|`number`|`extract`|Box 1g extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1h`|`number`|`extract`|Box 1h extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box1i`|`number`|`extract`|Box 1i extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box2`|`boolean`|`extract`|Box 2 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box3a`|`array`|`generate`|Box 3a extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box3a.*`|`string`|`extract`|||
|`Form1099DACopies.*.Transactions.*.Box3b`|`array`|`generate`|Box 3b extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box3b.*`|`string`|`extract`|||
|`Form1099DACopies.*.Transactions.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box5`|`boolean`|`extract`|Box 5 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box6`|`array`|`generate`|Box 6 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box6.*`|`string`|`extract`|||
|`Form1099DACopies.*.Transactions.*.Box7`|`boolean`|`extract`|Box 7 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box8`|`boolean`|`extract`|Box 8 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box9`|`boolean`|`extract`|Box 9 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box10`|`string`|`extract`|Box 10 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box11a`|`array`|`generate`|Box 11a extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box11a.*`|`string`|`extract`|||
|`Form1099DACopies.*.Transactions.*.Box11b`|`number`|`extract`|Box 11b extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box11c`|`number`|`extract`|Box 11c extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box12a`|`number`|`extract`|Box 12a extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box12b`|`date`|`extract`|Box 12b extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.Box13`|`string`|`extract`|Box 13 extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.StateTaxesWithheld`|`array`|`generate`|||
|`Form1099DACopies.*.Transactions.*.StateTaxesWithheld.*`|`object`|`generate`|State taxes withheld extracted from Form 1099-DA.||
|`Form1099DACopies.*.Transactions.*.StateTaxesWithheld.*.Box14`|`string`|`extract`|Box 14 extracted from Form 1099-DA.|WA|
|`Form1099DACopies.*.Transactions.*.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-DA.|12-3456789|
|`Form1099DACopies.*.Transactions.*.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-DA.|123456|
|`Form1099DACopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.||
