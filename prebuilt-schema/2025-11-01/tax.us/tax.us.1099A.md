| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099ACopies`|`array`|`generate`|Array of IRS Form 1099-A copy instances found in the document.||
|`Form1099ACopies.*`|`object`|`generate`|IRS Form 1099-A copy details.||
|`Form1099ACopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-A.|2025|
|`Form1099ACopies.*.CopyLabel`|`string`|`extract`|Form 1099-A copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099ACopies.*.Lender`|`object`|`generate`|||
|`Form1099ACopies.*.Lender.TIN`|`string`|`extract`|Lender tax identification number.|12-3456789|
|`Form1099ACopies.*.Lender.Name`|`string`|`extract`|Lender full name as written on the form.|WOODGROVE BANK|
|`Form1099ACopies.*.Lender.Address`|`string`|`extract`|Lender address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099ACopies.*.Lender.PhoneNumber`|`string`|`extract`|Lender Phone Number.|1-800-123-4567|
|`Form1099ACopies.*.Borrower`|`object`|`generate`|||
|`Form1099ACopies.*.Borrower.TIN`|`string`|`extract`|Borrower tax identification number.|XXX-XX-XXXX|
|`Form1099ACopies.*.Borrower.Name`|`string`|`extract`|Borrower full name as written on the form.|PASCALE WEYDERT|
|`Form1099ACopies.*.Borrower.Address`|`string`|`extract`|Borrower address.|FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099ACopies.*.Borrower.AccountNumber`|`string`|`extract`|Borrower account number.|i123456789|
|`Form1099ACopies.*.Box1`|`date`|`extract`|Box 1 extracted from Form 1099-A.|2022-01-01|
|`Form1099ACopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-A.|654321|
|`Form1099ACopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-A.|987654|
|`Form1099ACopies.*.Box5`|`boolean`|`extract`|If checked, the borrower was personally liable for repayment of the debt.|true|
|`Form1099ACopies.*.Box6`|`string`|`extract`|Description of property.|Flat 1B, 123 Main Street Seattle 98001 WA|
|`Form1099ACopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
