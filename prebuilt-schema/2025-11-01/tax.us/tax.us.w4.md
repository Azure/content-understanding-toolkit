**Analyzer ID:** `prebuilt-tax.us.w4`

**Description:** Employee's Withholding Certificate.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|The tax year for which this W-4 form is submitted.|2024|
|`Employee`|`object`|`generate`|Extracted employee information.||
|`Employee.FirstNameAndMiddleInitial`|`string`|`extract`|Employee's first name and middle initial as reported on the form.|John A|
|`Employee.LastName`|`string`|`extract`|Employee's last name as written on the form.|Doe|
|`Employee.Address`|`string`|`extract`|Employee's mailing address.|123 Main St, Springfield, IL 62704|
|`Employee.SSN`|`string`|`extract`|Employee's Social Security Number (SSN).|123-45-6789|
|`FilingStatus`|`array`|`generate`|Selected filing status options from Step 1(c). Use array to support zero/one selection in typical cases or multiple selections in edge cases.||
|`FilingStatus.*`|`string`|`extract`|||
|`Box2cIsChecked`|`boolean`|`extract`|Step 2(c) checkbox indicating only two jobs total (box on both W-4s).||
|`Box3`|`number`|`extract`|Total amount from Step 3 (dependents and other credits).|3000|
|`Box3ChildrenUnder17Amount`|`number`|`extract`|Amount for qualifying children under age 17 in Step 3.|2000|
|`Box3OtherDependentsAmount`|`number`|`extract`|Amount for other dependents in Step 3.|1000|
|`Box4a`|`number`|`extract`|Step 4(a): Other income (not from jobs) to consider for withholding.|5000|
|`Box4b`|`number`|`extract`|Step 4(b): Deductions other than the standard deduction.|10000|
|`Box4c`|`number`|`extract`|Step 4(c): Extra withholding per pay period.|200|
|`Employer`|`object`|`generate`|Extracted employer information.||
|`Employer.Name`|`string`|`extract`|Employer's name.|ABC Corp|
|`Employer.Address`|`string`|`extract`|Employer's mailing address.|123 Corporate Dr, Springfield, IL 62704|
|`Employer.EmploymentStartDate`|`date`|`extract`|The start date of employment for the employee.|2024-01-01|
|`Employer.EIN`|`string`|`extract`|Employer Identification Number (EIN).|12-3456789|
