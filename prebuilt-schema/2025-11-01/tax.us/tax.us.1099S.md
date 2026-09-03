**Analyzer ID:** `prebuilt-tax.us.1099S`

**Description:** Proceeds from Real Estate Transactions.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099SCopies`|`array`|`generate`|Array of IRS Form 1099-S copy instances found in the document.||
|`Form1099SCopies.*`|`object`|`generate`|IRS Form 1099-S copy details.||
|`Form1099SCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-S.|2025|
|`Form1099SCopies.*.CopyLabel`|`string`|`extract`|Form 1099-S copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099SCopies.*.Filer`|`object`|`generate`|||
|`Form1099SCopies.*.Filer.TIN`|`string`|`extract`|Filer tax identification number.|12-3456789|
|`Form1099SCopies.*.Filer.Name`|`string`|`extract`|Filer full name as written on the form.|WOODGROVE BANK|
|`Form1099SCopies.*.Filer.Address`|`string`|`extract`|Filer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099SCopies.*.Filer.PhoneNumber`|`string`|`extract`|Filer Phone Number.|1-800-123-4567|
|`Form1099SCopies.*.Transferor`|`object`|`generate`|||
|`Form1099SCopies.*.Transferor.TIN`|`string`|`extract`|Transferor tax identification number.|XXX-XX-1234|
|`Form1099SCopies.*.Transferor.Name`|`string`|`extract`|Transferor full name as written on the form.|PASCALE WEYDERT|
|`Form1099SCopies.*.Transferor.Address`|`string`|`extract`|Transferor address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099SCopies.*.Transferor.AccountNumber`|`string`|`extract`|Transferor account number.|i123456789|
|`Form1099SCopies.*.Box1`|`date`|`extract`|Box 1 extracted from Form 1099-S.|2025-12-31|
|`Form1099SCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-S.|654321|
|`Form1099SCopies.*.Box3`|`string`|`extract`|Box 3 extracted from Form 1099-S.|123 First Ave, Seattle, WA 98001|
|`Form1099SCopies.*.Box4`|`boolean`|`extract`|Transferor received or will receive property or services as part of the consideration (if checked).|false|
|`Form1099SCopies.*.Box5`|`boolean`|`extract`|If checked, transferor is a foreign person (nonresident alien, foreign partnership, foreign estate, or foreign trust).|true|
|`Form1099SCopies.*.Box6`|`number`|`extract`|Buyer's part of real estate tax.|500000|
|`Form1099SCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
