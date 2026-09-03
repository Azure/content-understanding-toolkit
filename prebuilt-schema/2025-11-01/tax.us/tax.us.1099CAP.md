**Analyzer ID:** `prebuilt-tax.us.1099CAP`

**Description:** Changes in Corporate Control and Capital Structure.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099CAPCopies`|`array`|`generate`|Array of IRS Form 1099-CAP copy instances found in the document.||
|`Form1099CAPCopies.*`|`object`|`generate`|IRS Form 1099-CAP copy details.||
|`Form1099CAPCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-CAP.|2025|
|`Form1099CAPCopies.*.CopyLabel`|`string`|`extract`|Form 1099-CAP copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099CAPCopies.*.Corporation`|`object`|`generate`|||
|`Form1099CAPCopies.*.Corporation.TIN`|`string`|`extract`|Corporation tax identification number.|12-3456789|
|`Form1099CAPCopies.*.Corporation.Name`|`string`|`extract`|Corporation full name as written on the form.|WOODGROVE BANK|
|`Form1099CAPCopies.*.Corporation.Address`|`string`|`extract`|Corporation address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099CAPCopies.*.Corporation.PhoneNumber`|`string`|`extract`|Corporation Phone Number.|1-800-123-4567|
|`Form1099CAPCopies.*.Shareholder`|`object`|`generate`|||
|`Form1099CAPCopies.*.Shareholder.TIN`|`string`|`extract`|Shareholder tax identification number.|XXX-XX-XXXX|
|`Form1099CAPCopies.*.Shareholder.Name`|`string`|`extract`|Shareholder full name as written on the form.|PASCALE WEYDERT|
|`Form1099CAPCopies.*.Shareholder.Address`|`string`|`extract`|Shareholder address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099CAPCopies.*.Shareholder.AccountNumber`|`string`|`extract`|Shareholder account number.|i123456789|
|`Form1099CAPCopies.*.Box1`|`date`|`extract`|Box 1 extracted from Form 1099-CAP.|2025-01-01|
|`Form1099CAPCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-CAP.|123456|
|`Form1099CAPCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-CAP.|654.32|
|`Form1099CAPCopies.*.Box4`|`string`|`extract`|Box 4 extracted from Form 1099-CAP.|A|
|`Form1099CAPCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|true|
