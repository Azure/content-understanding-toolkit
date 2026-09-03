**Analyzer ID:** `prebuilt-tax.us.1095C`

**Description:** Employer-Provided Health Insurance.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1095-C.|2024|
|`IsVoid`|`boolean`|`extract`|Indicates if the form is void.||
|`IsCorrected`|`boolean`|`extract`|Indicates if the form is corrected.||
|`Employee`|`object`|`generate`|Extracted employee information.||
|`Employee.FirstName`|`string`|`extract`|Employee's first name.|John|
|`Employee.MiddleInitial`|`string`|`extract`|Employee's middle initial.|D|
|`Employee.LastName`|`string`|`extract`|Employee's last name.|Doe|
|`Employee.SSN`|`string`|`extract`|Employee's Social Security Number.|123-45-6789|
|`Employee.Address`|`string`|`extract`|Employee's address as written on the form.|123 Microsoft Way, Redmond WA 98052|
|`Employee.AgeOnJanuary1`|`integer`|`extract`|Employee's age as of January 1 of the tax year.|40|
|`Employer`|`object`|`generate`|Extracted employer information.||
|`Employer.Name`|`string`|`extract`|Employer's name.|Microsoft Corp.|
|`Employer.EIN`|`string`|`extract`|Employer Identification Number.|12-3456789|
|`Employer.ContactPhoneNumber`|`string`|`extract`|Employer's contact phone number.|1-800-123-4567|
|`Employer.Address`|`string`|`extract`|Employer's address as written on the form.|456 Microsoft Way, Redmond WA 98052|
|`PlanStartMonth`|`integer`|`extract`|Month the employer's plan started.|1|
|`OfferOfCoverage`|`object`|`generate`|Extracted offer of coverage information.||
|`OfferOfCoverage.All12Months`|`string`|`extract`|Offer of coverage for all 12 months.|1A|
|`OfferOfCoverage.January`|`string`|`extract`|Offer of coverage for January.|1A|
|`OfferOfCoverage.February`|`string`|`extract`|Offer of coverage for February.|1A|
|`OfferOfCoverage.March`|`string`|`extract`|Offer of coverage for March.|1A|
|`OfferOfCoverage.April`|`string`|`extract`|Offer of coverage for April.|1A|
|`OfferOfCoverage.May`|`string`|`extract`|Offer of coverage for May.|1A|
|`OfferOfCoverage.June`|`string`|`extract`|Offer of coverage for June.|1A|
|`OfferOfCoverage.July`|`string`|`extract`|Offer of coverage for July.|1A|
|`OfferOfCoverage.August`|`string`|`extract`|Offer of coverage for August.|1A|
|`OfferOfCoverage.September`|`string`|`extract`|Offer of coverage for September.|1A|
|`OfferOfCoverage.October`|`string`|`extract`|Offer of coverage for October.|1A|
|`OfferOfCoverage.November`|`string`|`extract`|Offer of coverage for November.|1A|
|`OfferOfCoverage.December`|`string`|`extract`|Offer of coverage for December.|1A|
|`EmployeeRequiredContribution`|`object`|`generate`|Extracted employee required contribution information.||
|`EmployeeRequiredContribution.All12Months`|`number`|`extract`|Employee's required contribution for all 12 months.|100|
|`EmployeeRequiredContribution.January`|`number`|`extract`|Employee's required contribution for January.|100|
|`EmployeeRequiredContribution.February`|`number`|`extract`|Employee's required contribution for February.|100|
|`EmployeeRequiredContribution.March`|`number`|`extract`|Employee's required contribution for March.|100|
|`EmployeeRequiredContribution.April`|`number`|`extract`|Employee's required contribution for April.|100|
|`EmployeeRequiredContribution.May`|`number`|`extract`|Employee's required contribution for May.|100|
|`EmployeeRequiredContribution.June`|`number`|`extract`|Employee's required contribution for June.|100|
|`EmployeeRequiredContribution.July`|`number`|`extract`|Employee's required contribution for July.|100|
|`EmployeeRequiredContribution.August`|`number`|`extract`|Employee's required contribution for August.|100|
|`EmployeeRequiredContribution.September`|`number`|`extract`|Employee's required contribution for September.|100|
|`EmployeeRequiredContribution.October`|`number`|`extract`|Employee's required contribution for October.|100|
|`EmployeeRequiredContribution.November`|`number`|`extract`|Employee's required contribution for November.|100|
|`EmployeeRequiredContribution.December`|`number`|`extract`|Employee's required contribution for December.|100|
|`Section4980HSafeHarborAndOtherRelief`|`object`|`generate`|Extracted Section 4980H safe harbor and other relief information.||
|`Section4980HSafeHarborAndOtherRelief.All12Months`|`string`|`extract`|Section 4980H safe harbor and other relief for all 12 months.|2C|
|`Section4980HSafeHarborAndOtherRelief.January`|`string`|`extract`|Section 4980H safe harbor and other relief for January.|2C|
|`Section4980HSafeHarborAndOtherRelief.February`|`string`|`extract`|Section 4980H safe harbor and other relief for February.|2C|
|`Section4980HSafeHarborAndOtherRelief.March`|`string`|`extract`|Section 4980H safe harbor and other relief for March.|2C|
|`Section4980HSafeHarborAndOtherRelief.April`|`string`|`extract`|Section 4980H safe harbor and other relief for April.|2C|
|`Section4980HSafeHarborAndOtherRelief.May`|`string`|`extract`|Section 4980H safe harbor and other relief for May.|2C|
|`Section4980HSafeHarborAndOtherRelief.June`|`string`|`extract`|Section 4980H safe harbor and other relief for June.|2C|
|`Section4980HSafeHarborAndOtherRelief.July`|`string`|`extract`|Section 4980H safe harbor and other relief for July.|2C|
|`Section4980HSafeHarborAndOtherRelief.August`|`string`|`extract`|Section 4980H safe harbor and other relief for August.|2C|
|`Section4980HSafeHarborAndOtherRelief.September`|`string`|`extract`|Section 4980H safe harbor and other relief for September.|2C|
|`Section4980HSafeHarborAndOtherRelief.October`|`string`|`extract`|Section 4980H safe harbor and other relief for October.|2C|
|`Section4980HSafeHarborAndOtherRelief.November`|`string`|`extract`|Section 4980H safe harbor and other relief for November.|2C|
|`Section4980HSafeHarborAndOtherRelief.December`|`string`|`extract`|Section 4980H safe harbor and other relief for December.|2C|
|`ZIPCode`|`object`|`generate`|Extracted ZIP Code information.||
|`ZIPCode.All12Months`|`string`|`extract`|ZIP Code for all 12 months.|62704|
|`ZIPCode.January`|`string`|`extract`|ZIP Code for January.|62704|
|`ZIPCode.February`|`string`|`extract`|ZIP Code for February.|62704|
|`ZIPCode.March`|`string`|`extract`|ZIP Code for March.|62704|
|`ZIPCode.April`|`string`|`extract`|ZIP Code for April.|62704|
|`ZIPCode.May`|`string`|`extract`|ZIP Code for May.|62704|
|`ZIPCode.June`|`string`|`extract`|ZIP Code for June.|62704|
|`ZIPCode.July`|`string`|`extract`|ZIP Code for July.|62704|
|`ZIPCode.August`|`string`|`extract`|ZIP Code for August.|62704|
|`ZIPCode.September`|`string`|`extract`|ZIP Code for September.|62704|
|`ZIPCode.October`|`string`|`extract`|ZIP Code for October.|62704|
|`ZIPCode.November`|`string`|`extract`|ZIP Code for November.|62704|
|`ZIPCode.December`|`string`|`extract`|ZIP Code for December.|62704|
|`IsEmployerProvidedSelfInsuredCoverage`|`boolean`|`extract`|Indicates if the employer provides self-insured coverage.||
|`CoveredIndividuals`|`array`|`generate`|Covered individuals listed on Form 1095-C.||
|`CoveredIndividuals.*`|`object`|`generate`|Extracted covered individual information.||
|`CoveredIndividuals.*.FirstName`|`string`|`extract`|Covered individual's first name.|Jane|
|`CoveredIndividuals.*.MiddleInitial`|`string`|`extract`|Covered individual's middle initial.|D|
|`CoveredIndividuals.*.LastName`|`string`|`extract`|Covered individual's last name.|Doe|
|`CoveredIndividuals.*.SSNOrOtherTIN`|`string`|`extract`|Covered individual's SSN or other TIN.|123-45-6789|
|`CoveredIndividuals.*.BirthDate`|`date`|`extract`|Covered individual's birth date.|1975-01-01|
|`CoveredIndividuals.*.IsCoveredAll12Months`|`boolean`|`extract`|Indicates if the individual was covered for all 12 months.||
|`CoveredIndividuals.*.IsCoveredJanuary`|`boolean`|`extract`|Indicates coverage for January.||
|`CoveredIndividuals.*.IsCoveredFebruary`|`boolean`|`extract`|Indicates coverage for February.||
|`CoveredIndividuals.*.IsCoveredMarch`|`boolean`|`extract`|Indicates coverage for March.||
|`CoveredIndividuals.*.IsCoveredApril`|`boolean`|`extract`|Indicates coverage for April.||
|`CoveredIndividuals.*.IsCoveredMay`|`boolean`|`extract`|Indicates coverage for May.||
|`CoveredIndividuals.*.IsCoveredJune`|`boolean`|`extract`|Indicates coverage for June.||
|`CoveredIndividuals.*.IsCoveredJuly`|`boolean`|`extract`|Indicates coverage for July.||
|`CoveredIndividuals.*.IsCoveredAugust`|`boolean`|`extract`|Indicates coverage for August.||
|`CoveredIndividuals.*.IsCoveredSeptember`|`boolean`|`extract`|Indicates coverage for September.||
|`CoveredIndividuals.*.IsCoveredOctober`|`boolean`|`extract`|Indicates coverage for October.||
|`CoveredIndividuals.*.IsCoveredNovember`|`boolean`|`extract`|Indicates coverage for November.||
|`CoveredIndividuals.*.IsCoveredDecember`|`boolean`|`extract`|Indicates coverage for December.||
