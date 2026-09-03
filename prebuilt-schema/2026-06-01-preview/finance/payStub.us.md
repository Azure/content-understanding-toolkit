**Analyzer ID:** `prebuilt-payStub.us`

**Description:** US pay stubs and earnings statements.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`EmployeeAddress`|`string`|`extract`|Address of the employee|123 Maple Street, Springfield, IL, 62701|
|`EmployeeName`|`string`|`extract`|Name of the employee|John A. Doe|
|`EmployeeSSN`|`string`|`extract`|Social security number of the employee|123-45-6789|
|`EmployerAddress`|`string`|`extract`|Address of the employer|456 Oak Avenue, Metropolis, NY, 10101|
|`EmployerName`|`string`|`extract`|Listed name of the employer|Contoso Corporation|
|`PayDate`|`date`|`extract`|Date of salary payment|Feb. 26, 2020|
|`PayPeriodStartDate`|`date`|`extract`|Start date of the pay period|Feb. 19, 2020|
|`PayPeriodEndDate`|`date`|`extract`|End date of the pay period|Feb. 25, 2020|
|`CurrentPeriodGrossPay`|`number`|`extract`|Gross pay of the current period|$744.10|
|`YearToDateGrossPay`|`number`|`extract`|Year-to-date gross pay|$2744.10|
|`CurrentPeriodTaxes`|`number`|`extract`|Taxes of the current period|$410.10|
|`YearToDateTaxes`|`number`|`extract`|Year-to-date taxes|$855.90|
|`CurrentPeriodDeductions`|`number`|`extract`|Deductions of the current period|$410.10|
|`YearToDateDeductions`|`number`|`extract`|Year-to-date deductions|$855.90|
|`CurrentPeriodNetPay`|`number`|`extract`|Net pay of the current period|$744.10|
|`YearToDateNetPay`|`number`|`extract`|Year-to-date net pay|$2744.10|
