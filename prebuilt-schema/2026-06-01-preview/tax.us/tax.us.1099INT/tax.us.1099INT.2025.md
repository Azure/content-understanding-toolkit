| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099INTCopies`|`array`|`generate`|Array of IRS Form 1099-INT copy instances found in the document.||
|`Form1099INTCopies.*`|`object`|`generate`|IRS Form 1099-INT copy details.||
|`Form1099INTCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-INT.|2025|
|`Form1099INTCopies.*.CopyLabel`|`string`|`extract`|Form 1099-INT copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099INTCopies.*.Payer`|`object`|`generate`|||
|`Form1099INTCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099INTCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|CONTOSO BANK|
|`Form1099INTCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, Seattle, WA 98122-4567|
|`Form1099INTCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-206-123-4567|
|`Form1099INTCopies.*.Payer.RTN`|`string`|`extract`|Payer RTN|0123456789|
|`Form1099INTCopies.*.Recipient`|`object`|`generate`|||
|`Form1099INTCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|987-65-4321|
|`Form1099INTCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099INTCopies.*.Recipient.Address`|`string`|`extract`|Recipient address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-4567|
|`Form1099INTCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099INTCopies.*.Transactions`|`array`|`generate`|List of transactions reported in the Form 1099-INT||
|`Form1099INTCopies.*.Transactions.*`|`object`|`generate`|||
|`Form1099INTCopies.*.Transactions.*.IsFATCAFilingRequired`|`boolean`|`extract`|Is FATCA Filing Required extracted from Form 1099-INT.|true|
|`Form1099INTCopies.*.Transactions.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-INT.|123456|
|`Form1099INTCopies.*.Transactions.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-INT.|54321|
|`Form1099INTCopies.*.Transactions.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-INT.|654|
|`Form1099INTCopies.*.Transactions.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-INT.|987|
|`Form1099INTCopies.*.Transactions.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-INT.|963|
|`Form1099INTCopies.*.Transactions.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-INT.|753|
|`Form1099INTCopies.*.Transactions.*.Box7`|`string`|`extract`|Box 7 extracted from Form 1099-INT.|U.S.|
|`Form1099INTCopies.*.Transactions.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-INT.|852|
|`Form1099INTCopies.*.Transactions.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-INT.|973|
|`Form1099INTCopies.*.Transactions.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-INT.|753|
|`Form1099INTCopies.*.Transactions.*.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-INT.|741|
|`Form1099INTCopies.*.Transactions.*.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-INT.|147|
|`Form1099INTCopies.*.Transactions.*.Box13`|`number`|`extract`|Box 13 extracted from Form 1099-INT.|369|
|`Form1099INTCopies.*.Transactions.*.Box14`|`string`|`extract`|Box 14 extracted from Form 1099-INT.|0516273849|
|`Form1099INTCopies.*.Transactions.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-INT||
|`Form1099INTCopies.*.Transactions.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099INTCopies.*.Transactions.*.StateTaxesWithheld.*.Box15`|`string`|`extract`|Box 15 extracted from Form 1099-INT.|WA|
|`Form1099INTCopies.*.Transactions.*.StateTaxesWithheld.*.Box16`|`string`|`extract`|Box 16 extracted from Form 1099-INT.|123456789|
|`Form1099INTCopies.*.Transactions.*.StateTaxesWithheld.*.Box17`|`number`|`extract`|Box 17 extracted from Form 1099-INT.|321|
|`Form1099INTCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
