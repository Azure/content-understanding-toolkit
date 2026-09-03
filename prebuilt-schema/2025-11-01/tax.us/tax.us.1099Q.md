**Analyzer ID:** `prebuilt-tax.us.1099Q`

**Description:** Payments from Qualified Education Programs.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099QCopies`|`array`|`generate`|Array of IRS Form 1099-Q copy instances found in the document.||
|`Form1099QCopies.*`|`object`|`generate`|IRS Form 1099-Q copy details.||
|`Form1099QCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-Q.|2025|
|`Form1099QCopies.*.CopyLabel`|`string`|`extract`|Form 1099-Q copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099QCopies.*.Payer`|`object`|`generate`|||
|`Form1099QCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099QCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099QCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099QCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099QCopies.*.Recipient`|`object`|`generate`|||
|`Form1099QCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099QCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099QCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099QCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099QCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-Q.|123456|
|`Form1099QCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-Q.|321.65|
|`Form1099QCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-Q.|987.24|
|`Form1099QCopies.*.Box4`|`array`|`generate`|Trustee-to-trustee transfer selection(s).||
|`Form1099QCopies.*.Box4.*`|`string`|`extract`||TrusteeToTrustee|
|`Form1099QCopies.*.Box5`|`array`|`generate`|Distribution type selection(s).||
|`Form1099QCopies.*.Box5.*`|`string`|`extract`||CoverdellEsa|
|`Form1099QCopies.*.Box6`|`boolean`|`extract`|Check if the recipient is not the designated beneficiary.|false|
|`Form1099QCopies.*.FairMarketValue`|`string`|`extract`|Fair Market Value extracted from Form 1099-Q.|$123,456.00 DC1|
|`Form1099QCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
|`Form1099QCopies.*.DistributionCode`|`string`|`extract`|Distribution Code extracted from Form 1099-Q.|1|
