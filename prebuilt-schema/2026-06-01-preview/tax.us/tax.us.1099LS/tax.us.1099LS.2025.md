**Analyzer ID:** `prebuilt-tax.us.1099LS.2025`

**Description:** Extract tax US 1099 ls document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099LSCopies`|`array`|`generate`|Array of IRS Form 1099-LS copy instances found in the document.||
|`Form1099LSCopies.*`|`object`|`generate`|IRS Form 1099-LS copy details.||
|`Form1099LSCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-LS.|2025|
|`Form1099LSCopies.*.CopyLabel`|`string`|`extract`|Form 1099-LS copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099LSCopies.*.Acquirer`|`object`|`generate`|||
|`Form1099LSCopies.*.Acquirer.TIN`|`string`|`extract`|Acquirer tax identification number.|12-3456789|
|`Form1099LSCopies.*.Acquirer.Name`|`string`|`extract`|Acquirer full name as written on the form.|WOODGROVE BANK|
|`Form1099LSCopies.*.Acquirer.Address`|`string`|`extract`|Acquirer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099LSCopies.*.Acquirer.PhoneNumber`|`string`|`extract`|Acquirer Phone Number.|1-800-123-4567|
|`Form1099LSCopies.*.Recipient`|`object`|`generate`|||
|`Form1099LSCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099LSCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099LSCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099LSCopies.*.PolicyNumber`|`string`|`extract`|Policy Number extracted from Form 1099-LS.|i123456789|
|`Form1099LSCopies.*.IssuerName`|`string`|`extract`|Issuer Name extracted from Form 1099-LS.|CONTOSO|
|`Form1099LSCopies.*.AcquirerInformation`|`object`|`extract`|||
|`Form1099LSCopies.*.AcquirerInformation.Name`|`string`|`extract`|Acquirer's information contact name extracted from Form 1099-LS.|WOODGROVE BANK|
|`Form1099LSCopies.*.AcquirerInformation.Address`|`string`|`extract`|Acquirer's information contact address extracted from Form 1099-LS.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099LSCopies.*.AcquirerInformation.PhoneNumber`|`string`|`extract`|Acquirer's information contact phone number extracted from Form 1099-LS.|1-800-123-4567|
|`Form1099LSCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-LS.|654321|
|`Form1099LSCopies.*.Box2`|`date`|`extract`|Box 2 extracted from Form 1099-LS.|2025-02-01|
|`Form1099LSCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
