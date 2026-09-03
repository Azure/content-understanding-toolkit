**Analyzer ID:** `prebuilt-tax.us.w2`

**Description:** Wage and Tax Statement.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`W2Copies`|`array`|`generate`|Array of IRS W-2 copy instances found in the document.||
|`W2Copies.*`|`object`|`generate`|IRS W-2 copy details.||
|`W2Copies.*.FormVariant`|`string`|`extract`|IRS W2 Form variant. This field can have the one of the following values: 'W-2', 'W-2AS', 'W-2CM', 'W-2GU' or 'W-2VI'|W-2|
|`W2Copies.*.TaxYear`|`string`|`extract`|Form tax year|2021|
|`W2Copies.*.CopyLabel`|`string`|`extract`|W2 form copy version along with printed instruction related to this copy|Copy A—For Social Security Administration|
|`W2Copies.*.Employee`|`object`|`generate`|||
|`W2Copies.*.Employee.SSN`|`string`|`extract`|Employee Social Security Number. IRS W2 form field a|123-45-6789|
|`W2Copies.*.Employee.Name`|`string`|`extract`|Employee's first name, middle full/initials name, last name and suffix. IRS W2 form field e|John Contonso|
|`W2Copies.*.Employee.Address`|`string`|`extract`|Employee's address. Part of IRS W2 form field f.|123 Microsoft way, Redmond WA, 98123|
|`W2Copies.*.ControlNumber`|`string`|`extract`|W2 Form control number. IRS W2 form field d|0AB12 D345 7890|
|`W2Copies.*.Employer`|`object`|`generate`|||
|`W2Copies.*.Employer.EIN`|`string`|`extract`|Employer's identification number (EIN). IRS W2 form field b|12-3456789|
|`W2Copies.*.Employer.Name`|`string`|`extract`|Employer's name. Part of IRS W2 form field c|Fabrikam|
|`W2Copies.*.Employer.Address`|`string`|`extract`|Employer's address. Part of IRS W2 form field c.|321 Microsoft way, Redmond WA, 98123|
|`W2Copies.*.WagesTipsAndOtherCompensation`|`number`|`extract`|Wages, tips, and other compensation amount in USD. IRS W2 form field 1|1234567.89|
|`W2Copies.*.FederalIncomeTaxWithheld`|`number`|`extract`|Federal income tax withheld amount in USD. IRS W2 form field 2|1234567.89|
|`W2Copies.*.SocialSecurityWages`|`number`|`extract`|Social security wages amount in USD. IRS W2 form field 3|1234567.89|
|`W2Copies.*.SocialSecurityTaxWithheld`|`number`|`extract`|Social security tax withheld amount in USD. IRS W2 form field 4|1234567.89|
|`W2Copies.*.MedicareWagesAndTips`|`number`|`extract`|Medicare wages and tips amount in USD. IRS W2 form field 5|1234567.89|
|`W2Copies.*.MedicareTaxWithheld`|`number`|`extract`|Medicare tax withheld amount in USD. IRS W2 form field 6|1234567.89|
|`W2Copies.*.SocialSecurityTips`|`number`|`extract`|Social security tips amount in USD. IRS W2 form field 7|1234567.89|
|`W2Copies.*.AllocatedTips`|`number`|`extract`|Allocated tips in USD. IRS W2 form field 8|1234567.89|
|`W2Copies.*.DependentCareBenefits`|`number`|`extract`|Dependent care benefits amount in USD. IRS W2 form field 10|1234567.89|
|`W2Copies.*.NonQualifiedPlans`|`number`|`extract`|Non-qualified plans amount in USD. IRS W2 form field 11|1234567.89|
|`W2Copies.*.AdditionalInfo`|`array`|`generate`|Array holding W2 box 12 codes and amounts. IRS W2 form field 12||
|`W2Copies.*.AdditionalInfo.*`|`object`|`generate`|||
|`W2Copies.*.AdditionalInfo.*.LetterCode`|`string`|`extract`|Please refer to https://www.irs.gov/pub/irs-pdf/iw2w3.pdf for more details on IRS W2 box 12's letter code|A|
|`W2Copies.*.AdditionalInfo.*.Amount`|`number`|`extract`|Code amount in USD|1234567.89|
|`W2Copies.*.IsStatutoryEmployee`|`boolean`|`extract`|Part of IRS W2 form field 13. True if Statutory employee is checked|true|
|`W2Copies.*.IsRetirementPlan`|`boolean`|`extract`|Part of IRS W2 form field 13. True if Retirement plan is checked|true|
|`W2Copies.*.IsThirdPartySickPay`|`boolean`|`extract`|Part of IRS W2 form field 13. True if Third-party sick pay is checked|true|
|`W2Copies.*.Other`|`array`|`generate`|W2 box 14 entries (each element is one label and optional amount as printed). IRS W2 form field 14.||
|`W2Copies.*.Other.*`|`string`|`extract`||DISINS 170.85|
|`W2Copies.*.StateTaxes`|`array`|`generate`|State tax-related information. Content of IRS W2 form fields 15 to 17||
|`W2Copies.*.StateTaxes.*`|`object`|`generate`|||
|`W2Copies.*.StateTaxes.*.StateCode`|`string`|`extract`|Two letter state code. Part of IRS W2 form field 15|WA|
|`W2Copies.*.StateTaxes.*.EmployerStateIdNumber`|`string`|`extract`|Employer state Id number. Part of IRS W2 form field 15|1234567|
|`W2Copies.*.StateTaxes.*.StateWagesTipsEtc`|`number`|`extract`|State wages, tips, etc amount in USD. IRS W2 form field 16|1234567.89|
|`W2Copies.*.StateTaxes.*.StateIncomeTax`|`number`|`extract`|State income tax amount in USD. IRS W2 form field 17|1234567.89|
|`W2Copies.*.LocalTaxes`|`array`|`generate`|Local tax-related information. Content of IRS W2 form fields 18 to 20||
|`W2Copies.*.LocalTaxes.*`|`object`|`generate`|||
|`W2Copies.*.LocalTaxes.*.LocalWagesTipsEtc`|`number`|`extract`|Local wages, tips, etc amount in USD. Part of IRS W2 form field 18|1234567.89|
|`W2Copies.*.LocalTaxes.*.LocalIncomeTax`|`number`|`extract`|Local income tax amount in USD. Part of IRS W2 form field 19|1234567.89|
|`W2Copies.*.LocalTaxes.*.LocalityName`|`string`|`extract`|Locality name. Part of IRS W2 form field 20|Redmond|
