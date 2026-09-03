**Analyzer ID:** `prebuilt-tax.us.1099H`

**Description:** Health Coverage Tax Credit Advance Payments.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099HCopies`|`array`|`generate`|Array of IRS Form 1099-H copy instances found in the document.||
|`Form1099HCopies.*`|`object`|`generate`|IRS Form 1099-H copy details.||
|`Form1099HCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-H.|2025|
|`Form1099HCopies.*.CopyLabel`|`string`|`extract`|Form 1099-H copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099HCopies.*.Issuer`|`object`|`generate`|||
|`Form1099HCopies.*.Issuer.TIN`|`string`|`extract`|Issuer tax identification number.|12-3456789|
|`Form1099HCopies.*.Issuer.Name`|`string`|`extract`|Issuer full name as written on the form.|STATE OF WASHINGTON - Department of Labour|
|`Form1099HCopies.*.Issuer.Address`|`string`|`extract`|Issuer address.|P.O. BOX 6543, Seattle, WA 98122-4567|
|`Form1099HCopies.*.Issuer.PhoneNumber`|`string`|`extract`|Issuer Phone Number.|206-123-4567|
|`Form1099HCopies.*.Recipient`|`object`|`generate`|||
|`Form1099HCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|987-65-4321|
|`Form1099HCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099HCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099HCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-H.|321654|
|`Form1099HCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-H.|12|
|`Form1099HCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-H.|1000.01|
|`Form1099HCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-H.|2000.02|
|`Form1099HCopies.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-H.|3000.03|
|`Form1099HCopies.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-H.|4000.04|
|`Form1099HCopies.*.Box7`|`number`|`extract`|Box 7 extracted from Form 1099-H.|5000.05|
|`Form1099HCopies.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-H.|6000.06|
|`Form1099HCopies.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-H.|7000.07|
|`Form1099HCopies.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-H.|8000.08|
|`Form1099HCopies.*.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-H.|9000.09|
|`Form1099HCopies.*.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-H.|10000.10|
|`Form1099HCopies.*.Box13`|`number`|`extract`|Box 13 extracted from Form 1099-H.|11000.11|
|`Form1099HCopies.*.Box14`|`number`|`extract`|Box 14 extracted from Form 1099-H.|12000.12|
|`Form1099HCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
