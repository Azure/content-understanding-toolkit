| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099RCopies`|`array`|`generate`|Array of IRS Form 1099-R copy instances found in the document.||
|`Form1099RCopies.*`|`object`|`generate`|IRS Form 1099-R copy details.||
|`Form1099RCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-R.|2025|
|`Form1099RCopies.*.CopyLabel`|`string`|`extract`|Form 1099-R copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099RCopies.*.Payer`|`object`|`generate`|||
|`Form1099RCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099RCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099RCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099RCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099RCopies.*.Recipient`|`object`|`generate`|||
|`Form1099RCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099RCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099RCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099RCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099RCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-R.|987321|
|`Form1099RCopies.*.Box2a`|`number`|`extract`|Box 2a extracted from Form 1099-R.|123456|
|`Form1099RCopies.*.Box2b`|`array`|`generate`|Taxable amount/distro selection(s).||
|`Form1099RCopies.*.Box2b.*`|`string`|`extract`||taxableAmountNotDetermined|
|`Form1099RCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-R.|654741|
|`Form1099RCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-R.|258369|
|`Form1099RCopies.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-R.|123|
|`Form1099RCopies.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-R.|654|
|`Form1099RCopies.*.Box7`|`string`|`extract`|Box 7 extracted from Form 1099-R.|6K|
|`Form1099RCopies.*.IsIRASEPSIMPLE`|`boolean`|`extract`|IRA/SEP/SIMPLE checkbox.|true|
|`Form1099RCopies.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-R.|965|
|`Form1099RCopies.*.Box8Percentage`|`number`|`extract`|Box8 Percentage extracted from Form 1099-R.|1.20|
|`Form1099RCopies.*.Box9a`|`number`|`extract`|Box 9a extracted from Form 1099-R.|12.03|
|`Form1099RCopies.*.Box9b`|`number`|`extract`|Box 9b extracted from Form 1099-R.|987|
|`Form1099RCopies.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-R.|456|
|`Form1099RCopies.*.Box11`|`string`|`extract`|Box 11 extracted from Form 1099-R.|2020|
|`Form1099RCopies.*.Box12`|`boolean`|`extract`|FATCA filing requirement.|true|
|`Form1099RCopies.*.Box13`|`date`|`extract`|Date of payment.|2025-12-31|
|`Form1099RCopies.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-R||
|`Form1099RCopies.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099RCopies.*.StateTaxesWithheld.*.Box14`|`number`|`extract`|Box 14 extracted from Form 1099-R.|123000|
|`Form1099RCopies.*.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-R.|WA/12-3456789|
|`Form1099RCopies.*.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-R.|654321|
|`Form1099RCopies.*.LocalTaxesWithheld`|`array`|`generate`|Local Taxes Withheld extracted from Form 1099-R||
|`Form1099RCopies.*.LocalTaxesWithheld.*`|`object`|`generate`|||
|`Form1099RCopies.*.LocalTaxesWithheld.*.Box17`|`number`|`extract`|Box 17 extracted from Form 1099-R.|852|
|`Form1099RCopies.*.LocalTaxesWithheld.*.Box18`|`string`|`extract`|Box 18 extracted from Form 1099-R.|SEA|
|`Form1099RCopies.*.LocalTaxesWithheld.*.Box19`|`number`|`extract`|Box 19 extracted from Form 1099-R.|32|
|`Form1099RCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
