**Analyzer ID:** `prebuilt-tax.us.1099K.2025`

**Description:** Extract tax US 1099 k document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1099KCopies`|`array`|`generate`|Array of IRS Form 1099-K copy instances found in the document.||
|`Form1099KCopies.*`|`object`|`generate`|IRS Form 1099-K copy details.||
|`Form1099KCopies.*.TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-K.|2025|
|`Form1099KCopies.*.CopyLabel`|`string`|`extract`|Form 1099-K copy version along with printed instruction related to this copy|Copy B — For Recipient|
|`Form1099KCopies.*.Filer`|`object`|`generate`|||
|`Form1099KCopies.*.Filer.TIN`|`string`|`extract`|Filer tax identification number.|12-3456789|
|`Form1099KCopies.*.Filer.Name`|`string`|`extract`|Filer full name as written on the form.|CONTOSO BANK|
|`Form1099KCopies.*.Filer.Address`|`string`|`extract`|Filer address.|P.O. BOX 6543, SEATTLE, WA 98122-4567|
|`Form1099KCopies.*.Filer.PhoneNumber`|`string`|`extract`|Filer Phone Number.|1-206-123-4567|
|`Form1099KCopies.*.Payee`|`object`|`generate`|||
|`Form1099KCopies.*.Payee.TIN`|`string`|`extract`|Payee tax identification number.|987-65-4321|
|`Form1099KCopies.*.Payee.Name`|`string`|`extract`|Payee full name as written on the form.|PASCALE WEYDERT|
|`Form1099KCopies.*.Payee.Address`|`string`|`extract`|Payee address.|123 FREMONT AVE, APT. 55, SEATTLE, WA 98001-0432|
|`Form1099KCopies.*.Payee.AccountNumber`|`string`|`extract`|Payee account number.|i123456789|
|`Form1099KCopies.*.FilerCategory`|`array`|`generate`|Filer category selection(s).||
|`Form1099KCopies.*.FilerCategory.*`|`string`|`extract`||paymentSettlementEntity|
|`Form1099KCopies.*.TransactionType`|`array`|`generate`|Transaction type selection(s).||
|`Form1099KCopies.*.TransactionType.*`|`string`|`extract`||thirdPartyNetwork|
|`Form1099KCopies.*.PSE`|`object`|`generate`|||
|`Form1099KCopies.*.PSE.Name`|`string`|`extract`|Payment Settlement Entity's full name as written on the form.|PAYMENT SETTLEMENT ENTITY NAME|
|`Form1099KCopies.*.PSE.PhoneNumber`|`string`|`extract`|Payment Settlement Entity's Phone Number.|1-800-123-4567|
|`Form1099KCopies.*.Box1a`|`number`|`extract`|Box 1a extracted from Form 1099-K.|987321|
|`Form1099KCopies.*.Box1b`|`number`|`extract`|Box 1b extracted from Form 1099-K.|123456|
|`Form1099KCopies.*.Box2`|`string`|`extract`|Box 2 extracted from Form 1099-K.|ABC|
|`Form1099KCopies.*.Box3`|`integer`|`extract`|Box 3 Number of payment transactions extracted from Form 1099-K.|985|
|`Form1099KCopies.*.Box4`|`number`|`extract`|Box 4 extracted from Form 1099-K.|65432.10|
|`Form1099KCopies.*.Box5a`|`number`|`extract`|Box 5a extracted from Form 1099-K.|1000.01|
|`Form1099KCopies.*.Box5b`|`number`|`extract`|Box 5b extracted from Form 1099-K.|2000.02|
|`Form1099KCopies.*.Box5c`|`number`|`extract`|Box 5c extracted from Form 1099-K.|3000.03|
|`Form1099KCopies.*.Box5d`|`number`|`extract`|Box 5d extracted from Form 1099-K.|4000.04|
|`Form1099KCopies.*.Box5e`|`number`|`extract`|Box 5e extracted from Form 1099-K.|5000.05|
|`Form1099KCopies.*.Box5f`|`number`|`extract`|Box 5f extracted from Form 1099-K.|6000.06|
|`Form1099KCopies.*.Box5g`|`number`|`extract`|Box 5g extracted from Form 1099-K.|7000.07|
|`Form1099KCopies.*.Box5h`|`number`|`extract`|Box 5h extracted from Form 1099-K.|8000.08|
|`Form1099KCopies.*.Box5i`|`number`|`extract`|Box 5i extracted from Form 1099-K.|9000.09|
|`Form1099KCopies.*.Box5j`|`number`|`extract`|Box 5j extracted from Form 1099-K.|10000.10|
|`Form1099KCopies.*.Box5k`|`number`|`extract`|Box 5k extracted from Form 1099-K.|11000.11|
|`Form1099KCopies.*.Box5l`|`number`|`extract`|Box 5l extracted from Form 1099-K.|12000.12|
|`Form1099KCopies.*.StateTaxesWithheld`|`array`|`generate`|State Taxes Withheld extracted from Form 1099-K||
|`Form1099KCopies.*.StateTaxesWithheld.*`|`object`|`generate`|||
|`Form1099KCopies.*.StateTaxesWithheld.*.Box6`|`string`|`extract`|Box 6 extracted from Form 1099-K.|WA|
|`Form1099KCopies.*.StateTaxesWithheld.*.Box7`|`string`|`extract`|Box 7 extracted from Form 1099-K.|123456789|
|`Form1099KCopies.*.StateTaxesWithheld.*.Box8`|`number`|`extract`|Box 8 extracted from Form 1099-K.|123|
|`Form1099KCopies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrective filing.|false|
