| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099NECCopies`|`array`|`generate`|Array of IRS Form 1099-NEC copy instances found in the document.||
|`Form1099NECCopies.*`|`object`|`generate`|IRS Form 1099-NEC copy details.||
|`Form1099NECCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-NEC.|2025|
|`Form1099NECCopies.*.CopyLabel`|`string`|`extract`|Form 1099-NEC copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099NECCopies.*.Payer`|`object`|`generate`|||
|`Form1099NECCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099NECCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099NECCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099NECCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099NECCopies.*.Recipient`|`object`|`generate`|||
|`Form1099NECCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099NECCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099NECCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099NECCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099NECCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-NEC.|654321|
|`Form1099NECCopies.*.Box2`|`boolean`|`extract`|Payer made direct sales totaling $5,000 or more of consumer products to recipient for resale.|true|
|`Form1099NECCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-NEC.|123456|
|`Form1099NECCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-NEC.|123456|
|`Form1099NECCopies.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-NEC||
|`Form1099NECCopies.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099NECCopies.*.StateTaxesWithheld.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-NEC.|123456|
|`Form1099NECCopies.*.StateTaxesWithheld.*.Box6`|`string`|`extract`|Box 6 extracted from Form 1099-NEC.|WA|
|`Form1099NECCopies.*.StateTaxesWithheld.*.Box7`|`number`|`extract`|Box 7 extracted from Form 1099-NEC.|987321|
|`Form1099NECCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
