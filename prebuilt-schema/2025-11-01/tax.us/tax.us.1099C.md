| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099CCopies`|`array`|`generate`|Array of IRS Form 1099-C copy instances found in the document.||
|`Form1099CCopies.*`|`object`|`generate`|IRS Form 1099-C copy details.||
|`Form1099CCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-C.|2025|
|`Form1099CCopies.*.CopyLabel`|`string`|`extract`|Form 1099-C copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099CCopies.*.Creditor`|`object`|`generate`|||
|`Form1099CCopies.*.Creditor.TIN`|`string`|`extract`|Creditor tax identification number.|12-3456789|
|`Form1099CCopies.*.Creditor.Name`|`string`|`extract`|Creditor full name as written on the form.|WOODGROVE BANK|
|`Form1099CCopies.*.Creditor.Address`|`string`|`extract`|Creditor address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099CCopies.*.Creditor.PhoneNumber`|`string`|`extract`|Creditor Phone Number.|1-800-123-4567|
|`Form1099CCopies.*.Debtor`|`object`|`generate`|||
|`Form1099CCopies.*.Debtor.TIN`|`string`|`extract`|Debtor tax identification number.|XXX-XX-XXXX|
|`Form1099CCopies.*.Debtor.Name`|`string`|`extract`|Debtor full name as written on the form.|PASCALE WEYDERT|
|`Form1099CCopies.*.Debtor.Address`|`string`|`extract`|Debtor address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099CCopies.*.Debtor.AccountNumber`|`string`|`extract`|Debtor account number.|i123456789|
|`Form1099CCopies.*.Box1`|`date`|`extract`|Box 1 extracted from Form 1099-C.|2025-01-01|
|`Form1099CCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-C.|987654|
|`Form1099CCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-C.|123456|
|`Form1099CCopies.*.Box4`|`string`|`extract`|Box 4 extracted from Form 1099-C.|Mortgage on real estate property at: Flat 1B, 123 Main Street Seattle 98001 WA|
|`Form1099CCopies.*.Box5`|`boolean`|`extract`|If checked, the debtor was personally liable for repayment of the debt.|false|
|`Form1099CCopies.*.Box6`|`string`|`extract`|Box 6 extracted from Form 1099-C.|A|
|`Form1099CCopies.*.Box7`|`number`|`extract`|Box 7 extracted from Form 1099-C.|1234567|
|`Form1099CCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
