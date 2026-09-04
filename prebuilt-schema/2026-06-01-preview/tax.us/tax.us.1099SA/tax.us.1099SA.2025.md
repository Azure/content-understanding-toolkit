**Analyzer ID:** `prebuilt-tax.us.1099SA.2025`

**Description:** Extract tax US 1099 sa document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099SACopies`|`array`|`generate`|Array of IRS Form 1099-SA copy instances found in the document.||
|`Form1099SACopies.*`|`object`|`generate`|IRS Form 1099-SA copy details.||
|`Form1099SACopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-SA.|2025|
|`Form1099SACopies.*.CopyLabel`|`string`|`extract`|Form 1099-SA copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099SACopies.*.Payer`|`object`|`generate`|||
|`Form1099SACopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099SACopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099SACopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099SACopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099SACopies.*.Recipient`|`object`|`generate`|||
|`Form1099SACopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099SACopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099SACopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099SACopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099SACopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-SA.|654321|
|`Form1099SACopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-SA.|12345|
|`Form1099SACopies.*.Box3`|`string`|`extract`|Box 3 extracted from Form 1099-SA.|MNO1|
|`Form1099SACopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-SA.|123|
|`Form1099SACopies.*.Box5`|`array`|`generate`|Account type selection(s).||
|`Form1099SACopies.*.Box5.*`|`string`|`extract`||archerMsa|
|`Form1099SACopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
