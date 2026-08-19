| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099SBCopies`|`array`|`generate`|Array of IRS Form 1099-SB copy instances found in the document.||
|`Form1099SBCopies.*`|`object`|`generate`|IRS Form 1099-SB copy details.||
|`Form1099SBCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-SB.|2025|
|`Form1099SBCopies.*.CopyLabel`|`string`|`extract`|Form 1099-SB copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099SBCopies.*.Issuer`|`object`|`generate`|||
|`Form1099SBCopies.*.Issuer.TIN`|`string`|`extract`|Issuer tax identification number.|12-3456789|
|`Form1099SBCopies.*.Issuer.Name`|`string`|`extract`|Issuer full name as written on the form.|WOODGROVE BANK|
|`Form1099SBCopies.*.Issuer.Address`|`string`|`extract`|Issuer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099SBCopies.*.Issuer.PhoneNumber`|`string`|`extract`|Issuer Phone Number.|1-800-123-4567|
|`Form1099SBCopies.*.Seller`|`object`|`generate`|||
|`Form1099SBCopies.*.Seller.TIN`|`string`|`extract`|Seller tax identification number.|XXX-XX-1234|
|`Form1099SBCopies.*.Seller.Name`|`string`|`extract`|Seller full name as written on the form.|PASCALE WEYDERT|
|`Form1099SBCopies.*.Seller.Address`|`string`|`extract`|Seller address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099SBCopies.*.PolicyNumber`|`string`|`extract`|Policy Number extracted from Form 1099-SB.|i123456789|
|`Form1099SBCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-SB.|654321|
|`Form1099SBCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-SB.|123321|
|`Form1099SBCopies.*.IssuerInformation`|`object`|`generate`|Issuer Contact Information extracted from Form 1099-SB.||
|`Form1099SBCopies.*.IssuerInformation.Name`|`string`|`extract`|Issuer Contact Name.|JANE DOE|
|`Form1099SBCopies.*.IssuerInformation.Address`|`string`|`extract`|Issuer Contact Address.|123 MAIN ST, ANYTOWN, USA 12345|
|`Form1099SBCopies.*.IssuerInformation.PhoneNumber`|`string`|`extract`|Issuer Contact Phone Number.|1-800-123-4567|
|`Form1099SBCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
