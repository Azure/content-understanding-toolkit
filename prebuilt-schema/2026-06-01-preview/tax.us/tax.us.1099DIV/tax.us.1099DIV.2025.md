| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099DIVCopies`|`array`|`generate`|Array of IRS Form 1099-DIV copy instances found in the document.||
|`Form1099DIVCopies.*`|`object`|`generate`|IRS Form 1099-DIV copy details.||
|`Form1099DIVCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-DIV.|2025|
|`Form1099DIVCopies.*.CopyLabel`|`string`|`extract`|Form 1099-DIV copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099DIVCopies.*.Payer`|`object`|`generate`|||
|`Form1099DIVCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099DIVCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|CONTOSO BANK|
|`Form1099DIVCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-4567|
|`Form1099DIVCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-206-123-4567|
|`Form1099DIVCopies.*.Recipient`|`object`|`generate`|||
|`Form1099DIVCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|987-65-4321|
|`Form1099DIVCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099DIVCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099DIVCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099DIVCopies.*.Transactions`|`array`|`generate`|List of transactions reported in the Form 1099-DIV||
|`Form1099DIVCopies.*.Transactions.*`|`object`|`generate`|||
|`Form1099DIVCopies.*.Transactions.*.Box1a`|`number`|`extract`|Box 1a extracted from Form 1099-DIV.|123456|
|`Form1099DIVCopies.*.Transactions.*.Box1b`|`number`|`extract`|Box 1b extracted from Form 1099-DIV.|321|
|`Form1099DIVCopies.*.Transactions.*.Box2a`|`number`|`extract`|Box 2a extracted from Form 1099-DIV.|654|
|`Form1099DIVCopies.*.Transactions.*.Box2b`|`number`|`extract`|Box 2b extracted from Form 1099-DIV.|987|
|`Form1099DIVCopies.*.Transactions.*.Box2c`|`number`|`extract`|Box 2c extracted from Form 1099-DIV.|741|
|`Form1099DIVCopies.*.Transactions.*.Box2d`|`number`|`extract`|Box 2d extracted from Form 1099-DIV.|852|
|`Form1099DIVCopies.*.Transactions.*.Box2e`|`number`|`extract`|Box 2e extracted from Form 1099-DIV.|369|
|`Form1099DIVCopies.*.Transactions.*.Box2f`|`number`|`extract`|Box 2f extracted from Form 1099-DIV.|258|
|`Form1099DIVCopies.*.Transactions.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-DIV.|159|
|`Form1099DIVCopies.*.Transactions.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-DIV.|1850.25|
|`Form1099DIVCopies.*.Transactions.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-DIV.|654|
|`Form1099DIVCopies.*.Transactions.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-DIV.|987|
|`Form1099DIVCopies.*.Transactions.*.Box7`|`number`|`extract`|Box 7 extracted from Form 1099-DIV.|731|
|`Form1099DIVCopies.*.Transactions.*.Box8`|`string`|`extract`|Box 8 extracted from Form 1099-DIV.|U.S.|
|`Form1099DIVCopies.*.Transactions.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-DIV.|761|
|`Form1099DIVCopies.*.Transactions.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-DIV.|943|
|`Form1099DIVCopies.*.Transactions.*.Box11`|`boolean`|`extract`|Box 11 extracted from Form 1099-DIV.|true|
|`Form1099DIVCopies.*.Transactions.*.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-DIV.|962|
|`Form1099DIVCopies.*.Transactions.*.Box13`|`number`|`extract`|Box 13 extracted from Form 1099-DIV.|123|
|`Form1099DIVCopies.*.Transactions.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-DIV||
|`Form1099DIVCopies.*.Transactions.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099DIVCopies.*.Transactions.*.StateTaxesWithheld.*.Box14`|`string`|`extract`|Box 14 extracted from Form 1099-DIV.|WA|
|`Form1099DIVCopies.*.Transactions.*.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-DIV.|123456789|
|`Form1099DIVCopies.*.Transactions.*.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-DIV.|321|
|`Form1099DIVCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
