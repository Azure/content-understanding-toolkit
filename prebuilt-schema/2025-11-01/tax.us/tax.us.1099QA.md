**Analyzer ID:** `prebuilt-tax.us.1099QA`

**Description:** Distributions from ABLE Accounts.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099QACopies`|`array`|`generate`|Array of IRS Form 1099-QA copy instances found in the document.||
|`Form1099QACopies.*`|`object`|`generate`|IRS Form 1099-QA copy details.||
|`Form1099QACopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-QA.|2025|
|`Form1099QACopies.*.CopyLabel`|`string`|`extract`|Form 1099-QA copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099QACopies.*.Payer`|`object`|`generate`|||
|`Form1099QACopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099QACopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099QACopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099QACopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099QACopies.*.Recipient`|`object`|`generate`|||
|`Form1099QACopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099QACopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099QACopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099QACopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099QACopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-QA.|321654|
|`Form1099QACopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-QA.|123|
|`Form1099QACopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-QA.|123456|
|`Form1099QACopies.*.Box4`|`boolean`|`extract`|Program-to-program transfer.|true|
|`Form1099QACopies.*.Box5`|`boolean`|`extract`|Check if ABLE account terminated in the calendar year reported.|true|
|`Form1099QACopies.*.Box6`|`boolean`|`extract`|Check if the recipient is not the designated beneficiary.|false|
|`Form1099QACopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
