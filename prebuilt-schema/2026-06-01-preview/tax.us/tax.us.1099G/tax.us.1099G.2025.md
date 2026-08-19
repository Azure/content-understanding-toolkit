| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099GCopies`|`array`|`generate`|Array of IRS Form 1099-G copy instances found in the document.||
|`Form1099GCopies.*`|`object`|`generate`|IRS Form 1099-G copy details.||
|`Form1099GCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-G.|2025|
|`Form1099GCopies.*.CopyLabel`|`string`|`extract`|Form 1099-G copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099GCopies.*.Payer`|`object`|`generate`|||
|`Form1099GCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099GCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|STATE OF WASHINGTON - Department of Labour|
|`Form1099GCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, Seattle, WA 98122-4567|
|`Form1099GCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|206-123-4567|
|`Form1099GCopies.*.Recipient`|`object`|`generate`|||
|`Form1099GCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|987-65-4321|
|`Form1099GCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099GCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099GCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|1123456789|
|`Form1099GCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-G.|123456|
|`Form1099GCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-G.|123456|
|`Form1099GCopies.*.Box3`|`string`|`extract`|Box 3 extracted from Form 1099-G.|2025|
|`Form1099GCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-G.|321|
|`Form1099GCopies.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-G.|951|
|`Form1099GCopies.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-G.|159|
|`Form1099GCopies.*.Box7`|`number`|`extract`|Box 7 extracted from Form 1099-G.|0|
|`Form1099GCopies.*.Box8`|`boolean`|`extract`|Box 8 extracted from Form 1099-G.|false|
|`Form1099GCopies.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-G.|987|
|`Form1099GCopies.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-G||
|`Form1099GCopies.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099GCopies.*.StateTaxesWithheld.*.Box10a`|`string`|`extract`|Box 10a extracted from Form 1099-G.|WA|
|`Form1099GCopies.*.StateTaxesWithheld.*.Box10b`|`string`|`extract`|Box 10b extracted from Form 1099-G.|123456789|
|`Form1099GCopies.*.StateTaxesWithheld.*.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-G.|321|
|`Form1099GCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
|`Form1099GCopies.*.IsSecondTINNotice`|`boolean`|`extract`|Second TIN Notice Checkbox extracted from Form 1099-G.|false|
