**Analyzer ID:** `prebuilt-tax.us.1095A.2025`

**Description:** Extract tax US 1095 a document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1095-A.|2024|
|`IsVoid`|`boolean`|`extract`|Indicates if the form is void.||
|`IsCorrected`|`boolean`|`extract`|Indicates if the form is corrected.||
|`MarketplaceIdentifier`|`string`|`extract`|Marketplace identifier extracted from Form 1095-A.|FLORIDA|
|`MarketplaceAssignedPolicyNumber`|`string`|`extract`|Marketplace assigned policy number extracted from Form 1095-A.|ABC123456789|
|`PolicyIssuerName`|`string`|`extract`|The issuer's name for the health insurance policy.|Health Insurance Co.|
|`PolicyStartDate`|`date`|`extract`|Policy start date extracted from Form 1095-A.|2024-01-01|
|`PolicyTerminationDate`|`date`|`extract`|Policy termination date extracted from Form 1095-A.|2024-12-31|
|`Recipient`|`object`|`generate`|Extracted recipient information.||
|`Recipient.Name`|`string`|`extract`|Recipient's full name as written on the form.|Jane Doe|
|`Recipient.SSN`|`string`|`extract`|Recipient's Social Security Number.|123-45-6789|
|`Recipient.BirthDate`|`date`|`extract`|Recipient's birth date.|1970-01-01|
|`Recipient.Address`|`string`|`extract`|Recipient's address as written on the form.|123 Microsoft Way, Redmond WA 98052|
|`Spouse`|`object`|`generate`|Extracted spouse information.||
|`Spouse.Name`|`string`|`extract`|Spouse's full name as written on the form.|John Doe|
|`Spouse.SSN`|`string`|`extract`|Spouse's Social Security Number.|987-65-4321|
|`Spouse.BirthDate`|`date`|`extract`|Spouse's birth date.|1975-02-01|
|`CoveredIndividuals`|`array`|`generate`|Covered individuals listed on Form 1095-A.||
|`CoveredIndividuals.*`|`object`|`generate`|Extracted covered individual information.||
|`CoveredIndividuals.*.Name`|`string`|`extract`|Full name of the covered individual as written on the form.|John Doe Jr.|
|`CoveredIndividuals.*.SSN`|`string`|`extract`|Social Security Number of the covered individual.|567-89-0123|
|`CoveredIndividuals.*.BirthDate`|`date`|`extract`|Birth date of the covered individual.|2005-03-15|
|`CoveredIndividuals.*.CoverageStartDate`|`date`|`extract`|Coverage start date of the covered individual.|2023-01-01|
|`CoveredIndividuals.*.CoverageTerminationDate`|`date`|`extract`|Coverage termination date of the covered individual.|2023-12-31|
|`Coverages`|`array`|`generate`|Coverage details extracted from Form 1095-A.||
|`Coverages.*`|`object`|`generate`|Extracted coverage details information.||
|`Coverages.*.Month`|`string`|`extract`|Month for which the coverage details apply.|January|
|`Coverages.*.MonthlyEnrollmentPremiums`|`number`|`extract`|Monthly enrollment premiums amount for the month.|500|
|`Coverages.*.MonthlySecondLowestCostSilverPlanPremium`|`number`|`extract`|Monthly Second Lowest Cost Silver Plan (SLCSP) premium.|450|
|`Coverages.*.MonthlyAdvancePaymentOfPremiumTaxCredit`|`number`|`extract`|Advance payment of premium tax credit amount for the month.|200|
