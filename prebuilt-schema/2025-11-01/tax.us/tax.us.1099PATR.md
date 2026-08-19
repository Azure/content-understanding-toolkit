| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099PATRCopies`|`array`|`generate`|Array of IRS Form 1099-PATR copy instances found in the document.||
|`Form1099PATRCopies.*`|`object`|`generate`|IRS Form 1099-PATR copy details.||
|`Form1099PATRCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-PATR.|2025|
|`Form1099PATRCopies.*.CopyLabel`|`string`|`extract`|Form 1099-PATR copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099PATRCopies.*.Payer`|`object`|`generate`|||
|`Form1099PATRCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099PATRCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099PATRCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099PATRCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099PATRCopies.*.Recipient`|`object`|`generate`|||
|`Form1099PATRCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099PATRCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099PATRCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099PATRCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099PATRCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-PATR.|123456|
|`Form1099PATRCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-PATR.|654|
|`Form1099PATRCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-PATR.|963|
|`Form1099PATRCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-PATR.|123987|
|`Form1099PATRCopies.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-PATR.|321|
|`Form1099PATRCopies.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-PATR.|852|
|`Form1099PATRCopies.*.Box7`|`number`|`extract`|Box 7 extracted from Form 1099-PATR.|741|
|`Form1099PATRCopies.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-PATR.|951|
|`Form1099PATRCopies.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-PATR.|159|
|`Form1099PATRCopies.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-PATR.|654|
|`Form1099PATRCopies.*.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-PATR.|321|
|`Form1099PATRCopies.*.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-PATR.|12|
|`Form1099PATRCopies.*.Box13`|`boolean`|`extract`|Specified Cooperative checkbox.|false|
|`Form1099PATRCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
