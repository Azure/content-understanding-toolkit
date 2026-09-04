**Analyzer ID:** `prebuilt-tax.us.1099OID`

**Description:** Original Issue Discount.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099OIDCopies`|`array`|`generate`|Array of IRS Form 1099-OID copy instances found in the document.||
|`Form1099OIDCopies.*`|`object`|`generate`|IRS Form 1099-OID copy details.||
|`Form1099OIDCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-OID.|2025|
|`Form1099OIDCopies.*.CopyLabel`|`string`|`extract`|Form 1099-OID copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099OIDCopies.*.Payer`|`object`|`generate`|||
|`Form1099OIDCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099OIDCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099OIDCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099OIDCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099OIDCopies.*.Recipient`|`object`|`generate`|||
|`Form1099OIDCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099OIDCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099OIDCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099OIDCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099OIDCopies.*.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-OID.|false|
|`Form1099OIDCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-OID.|654321|
|`Form1099OIDCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-OID.|123456|
|`Form1099OIDCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-OID.|12345|
|`Form1099OIDCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-OID.|6741|
|`Form1099OIDCopies.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-OID.|125|
|`Form1099OIDCopies.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-OID.|1.20|
|`Form1099OIDCopies.*.Box7`|`string`|`extract`|Box 7 extracted from Form 1099-OID.|NYC XYZ ESPP 10%|
|`Form1099OIDCopies.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-OID.|9875|
|`Form1099OIDCopies.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-OID.|951|
|`Form1099OIDCopies.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-OID.|123.56|
|`Form1099OIDCopies.*.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-OID.|987.20|
|`Form1099OIDCopies.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-OID||
|`Form1099OIDCopies.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099OIDCopies.*.StateTaxesWithheld.*.Box12`|`string`|`extract`|Box 12 extracted from Form 1099-OID.|WA|
|`Form1099OIDCopies.*.StateTaxesWithheld.*.Box13`|`string`|`extract`|Box 13 extracted from Form 1099-OID.|98-1234567|
|`Form1099OIDCopies.*.StateTaxesWithheld.*.Box14`|`number`|`extract`|Box 14 extracted from Form 1099-OID.|52123|
|`Form1099OIDCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
