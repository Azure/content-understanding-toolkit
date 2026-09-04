**Analyzer ID:** `prebuilt-tax.us.1098`

**Description:** Mortgage Interest Statement.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Form1098Copies`|`array`|`generate`|Array of IRS Form 1098 copy instances found in the document.||
|`Form1098Copies.*`|`object`|`generate`|IRS Form 1098 copy details.||
|`Form1098Copies.*.TaxYear`|`string`|`extract`|Form tax year|2021|
|`Form1098Copies.*.CopyLabel`|`string`|`extract`|Form 1098 copy version along with printed instruction related to this copy|Copy B — For Payer/Borrower|
|`Form1098Copies.*.Borrower`|`object`|`generate`|||
|`Form1098Copies.*.Borrower.TIN`|`string`|`extract`|Borrower's tax identification number|123-45-6789|
|`Form1098Copies.*.Borrower.Name`|`string`|`extract`|Borrower's full name as written on the form|John Smith|
|`Form1098Copies.*.Borrower.Address`|`string`|`extract`|Borrower's address|123 Microsoft Way, Redmond WA 98052|
|`Form1098Copies.*.Borrower.AccountNumber`|`string`|`extract`|Borrower's account number|55123456789|
|`Form1098Copies.*.Lender`|`object`|`generate`|||
|`Form1098Copies.*.Lender.TIN`|`string`|`extract`|Lender's tax identification number|12-3456789|
|`Form1098Copies.*.Lender.Name`|`string`|`extract`|Lender's name|Woodgrove Bank|
|`Form1098Copies.*.Lender.Address`|`string`|`extract`|Lender's address|321 Microsoft Way, Redmond WA 98052|
|`Form1098Copies.*.Lender.PhoneNumber`|`string`|`extract`|Lender's phone number|800-123-4567|
|`Form1098Copies.*.MortgageInterest`|`number`|`extract`|Mortgage interest amount received from payer(s)/borrower(s) (box 1)|3009.87|
|`Form1098Copies.*.OutstandingMortgagePrincipal`|`number`|`extract`|Outstanding mortgage principal (box 2)|654321|
|`Form1098Copies.*.MortgageOriginationDate`|`date`|`extract`|Origination date of the mortgage (box 3)|2021-01-15|
|`Form1098Copies.*.OverpaidInterestRefund`|`number`|`extract`|Refund amount of overpaid interest (box 4)|0|
|`Form1098Copies.*.MortgageInsurancePremium`|`number`|`extract`|Mortgage insurance premium amount (box 5)|0|
|`Form1098Copies.*.PointsPaid`|`number`|`extract`|Points paid on purchase of principal residence (box 6)|0|
|`Form1098Copies.*.IsPropertyAddressSameAsBorrower`|`boolean`|`extract`|Is the address of the property securing the mortgage the same as the payer's/borrower's mailing address (box 7)|true|
|`Form1098Copies.*.PropertyAddress`|`string`|`extract`|Address or description of the property securing the mortgage (box 8)|123 Main St, Redmond WA 98052|
|`Form1098Copies.*.MortgagedPropertiesCount`|`integer`|`extract`|Number of properties securing the mortgage (box 9)|1|
|`Form1098Copies.*.Other`|`string`|`extract`|Additional information to report to payer (box 10)|Real estate taxes paid from escrow|
|`Form1098Copies.*.MortgageAcquisitionDate`|`date`|`extract`|Mortgage acquisition date (box 11)|2021-06-15|
|`Form1098Copies.*.IsCorrected`|`boolean`|`extract`|Indicates whether form is a corrected filing|false|
