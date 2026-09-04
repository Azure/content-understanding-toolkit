**Analyzer ID:** `prebuilt-tax.us.1099MISC.2025`

**Description:** Extract tax US 1099 misc document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099MISCCopies`|`array`|`generate`|Array of IRS Form 1099-MISC copy instances found in the document.||
|`Form1099MISCCopies.*`|`object`|`generate`|IRS Form 1099-MISC copy details.||
|`Form1099MISCCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-MISC.|2025|
|`Form1099MISCCopies.*.CopyLabel`|`string`|`extract`|Form 1099-MISC copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099MISCCopies.*.Payer`|`object`|`generate`|||
|`Form1099MISCCopies.*.Payer.TIN`|`string`|`extract`|Payer tax identification number.|12-3456789|
|`Form1099MISCCopies.*.Payer.Name`|`string`|`extract`|Payer full name as written on the form.|WOODGROVE BANK|
|`Form1099MISCCopies.*.Payer.Address`|`string`|`extract`|Payer address captured as a single free-form string (normalized to string per guideline).|P.O. BOX 6543, SEATTLE, WA 98122-0123|
|`Form1099MISCCopies.*.Payer.PhoneNumber`|`string`|`extract`|Payer phone number captured as a string (normalized to string per guideline).|1-800-123-4567|
|`Form1099MISCCopies.*.Recipient`|`object`|`generate`|||
|`Form1099MISCCopies.*.Recipient.TIN`|`string`|`extract`|Recipient tax identification number.|XXX-XX-1234|
|`Form1099MISCCopies.*.Recipient.Name`|`string`|`extract`|Recipient full name as written on the form.|PASCALE WEYDERT|
|`Form1099MISCCopies.*.Recipient.Address`|`string`|`extract`|Recipient address captured as a single free-form string (normalized to string per guideline).|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-6543|
|`Form1099MISCCopies.*.Recipient.AccountNumber`|`string`|`extract`|Recipient account number.|i123456789|
|`Form1099MISCCopies.*.Box1`|`number`|`extract`|Box 1 extracted from Form 1099-MISC.|12365|
|`Form1099MISCCopies.*.Box2`|`number`|`extract`|Box 2 extracted from Form 1099-MISC.|98541.20|
|`Form1099MISCCopies.*.Box3`|`number`|`extract`|Box 3 extracted from Form 1099-MISC.|123|
|`Form1099MISCCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-MISC.|98587|
|`Form1099MISCCopies.*.Box5`|`number`|`extract`|Box 5 extracted from Form 1099-MISC.|365|
|`Form1099MISCCopies.*.Box6`|`number`|`extract`|Box 6 extracted from Form 1099-MISC.|942123|
|`Form1099MISCCopies.*.Box7`|`boolean`|`extract`|Payer made direct sales totaling $5,000 or more of consumer products to recipient for resale.|true|
|`Form1099MISCCopies.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-MISC.|698541|
|`Form1099MISCCopies.*.Box9`|`number`|`extract`|Box 9 extracted from Form 1099-MISC.|852|
|`Form1099MISCCopies.*.Box10`|`number`|`extract`|Box 10 extracted from Form 1099-MISC.|12|
|`Form1099MISCCopies.*.Box11`|`number`|`extract`|Box 11 extracted from Form 1099-MISC.|156|
|`Form1099MISCCopies.*.Box12`|`number`|`extract`|Box 12 extracted from Form 1099-MISC.|125|
|`Form1099MISCCopies.*.Box13`|`boolean`|`extract`|Box 13 extracted from Form 1099-MISC.|true|
|`Form1099MISCCopies.*.Box14`|`number`|`extract`|Nonqualified deferred compensation.|987654|
|`Form1099MISCCopies.*.Box15`|`number`|`extract`|Box 15 extracted from Form 1099-MISC.|874|
|`Form1099MISCCopies.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-MISC||
|`Form1099MISCCopies.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099MISCCopies.*.StateTaxesWithheld.*.Box16`|`number`|`extract`|Box 16 extracted from Form 1099-MISC.|654321|
|`Form1099MISCCopies.*.StateTaxesWithheld.*.Box17`|`string`|`extract`|Box 17 extracted from Form 1099-MISC.|WA|
|`Form1099MISCCopies.*.StateTaxesWithheld.*.Box18`|`number`|`extract`|Box 18 extracted from Form 1099-MISC.|1234567|
|`Form1099MISCCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
|`Form1099MISCCopies.*.IsSecondTINNotice`|`boolean`|`extract`|2nd TIN Notice Checkbox extracted from Form 1099-MISC.|false|
