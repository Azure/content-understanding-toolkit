**Analyzer ID:** `prebuilt-tax.us.1099LTC`

**Description:** Long-Term Care Benefits.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099LTCCopies`|`array`|`generate`|Array of IRS Form 1099-LTC copy instances found in the document.||
|`Form1099LTCCopies.*`|`object`|`generate`|IRS Form 1099-LTC copy details.||
|`Form1099LTCCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-LTC.|2025|
|`Form1099LTCCopies.*.CopyLabel`|`string`|`extract`|Form 1099-LTC copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099LTCCopies.*.Payer`|`object`|`generate`|||
|`Form1099LTCCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099LTCCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099LTCCopies.*.Payer.Address`|`string`|`extract`|Payer address.|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099LTCCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer Phone Number.|1-800-123-4567|
|`Form1099LTCCopies.*.Policyholder`|`object`|`generate`|||
|`Form1099LTCCopies.*.Policyholder.TIN`|`string`|`extract`|Policyholder tax identification number.|XXX-XX-1234|
|`Form1099LTCCopies.*.Policyholder.Name`|`string`|`extract`|Policyholder full name as written on the form.|PASCALE WEYDERT|
|`Form1099LTCCopies.*.Policyholder.Address`|`string`|`extract`|Policyholder address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099LTCCopies.*.Policyholder.AccountNumber`|`string`|`extract`|Policyholder account number.|i123456789|
|`Form1099LTCCopies.*.Insured`|`object`|`generate`|||
|`Form1099LTCCopies.*.Insured.TIN`|`string`|`extract`|Insured tax identification number.|XXX-XX-9876|
|`Form1099LTCCopies.*.Insured.Name`|`string`|`extract`|Insured full name as written on the form.|BOB WEYDERT|
|`Form1099LTCCopies.*.Insured.Address`|`string`|`extract`|Insured address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099LTCCopies.*.DateCertified`|`date`|`extract`|Date Certified extracted from Form 1099-LTC.|2025-12-21|
|`Form1099LTCCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-LTC.|654321|
|`Form1099LTCCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-LTC.|123456|
|`Form1099LTCCopies.*.Box3`|`array`|`generate`|Benefit type selection(s).||
|`Form1099LTCCopies.*.Box3.*`|`string`|`extract`||reimbursedAmount|
|`Form1099LTCCopies.*.Box4`|`boolean`|`extract`|Qualified contract (optional) checkbox.|true|
|`Form1099LTCCopies.*.Box5`|`array`|`generate`|Condition selection(s).||
|`Form1099LTCCopies.*.Box5.*`|`string`|`extract`||chronicallyIll|
|`Form1099LTCCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
