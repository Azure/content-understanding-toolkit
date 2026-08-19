| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`LenderLoanNumber`|`string`|`extract`|Lender loan number or universal loan identifier|265Fs6fAZ2H4984Gs4f23hQ811|
|`AgencyCaseNumber`|`string`|`extract`|Agency case number|115894|
|`Borrowers`|`array`|`generate`|List of extracted borrower information||
|`Borrowers.*`|`object`|`generate`|Extracted borrower information||
|`Borrowers.*.Name`|`string`|`extract`|Borrower's full name as written on the form|Gwen Stacy|
|`Borrowers.*.CoBorrowerNames`|`string`|`extract`|Co-borrower's full name(s) as written on the form|Carmen Leannon|
|`Borrowers.*.SSN`|`string`|`extract`|Borrower's social security number|557-99-7283|
|`Borrowers.*.BirthDate`|`date`|`extract`|Borrower's date of birth|1989-04-07|
|`Borrowers.*.CitizenshipType`|`array`|`generate`|Borrower's citizenship selection(s)||
|`Borrowers.*.CitizenshipType.*`|`string`|`extract`|||
|`Borrowers.*.CreditApplicationType`|`array`|`generate`|Borrower's credit application type selection(s)||
|`Borrowers.*.CreditApplicationType.*`|`string`|`extract`|||
|`Borrowers.*.NumberOfBorrowers`|`integer`|`extract`|Total number of borrowers|2|
|`Borrowers.*.MaritalStatus`|`array`|`generate`|Borrower's marital status selection(s)||
|`Borrowers.*.MaritalStatus.*`|`string`|`extract`|||
|`Borrowers.*.NumberOfDependents`|`integer`|`extract`|Total number of borrower's dependents|2|
|`Borrowers.*.DependentsAges`|`string`|`extract`|Ages of borrower's dependents|10, 11|
|`Borrowers.*.HomePhoneNumber`|`string`|`extract`|Borrower's home phone number|(489) 746-8900|
|`Borrowers.*.CellPhoneNumber`|`string`|`extract`|Borrower's cell phone number|(831) 728-4766|
|`Borrowers.*.WorkPhoneNumber`|`string`|`extract`|Borrower's work phone number|(987) 213-5674|
|`Borrowers.*.CurrentAddress`|`string`|`extract`|Borrower's current address|1634 W Glenoaks Blvd<br>Glendale CA 91201 United States|
|`Borrowers.*.YearsInCurrentAddress`|`integer`|`extract`|Years at current address|1|
|`Borrowers.*.MonthsInCurrentAddress`|`integer`|`extract`|Months at current address|2|
|`Borrowers.*.CurrentHousingExpenseType`|`array`|`generate`|Borrower's current housing expense selection(s)||
|`Borrowers.*.CurrentHousingExpenseType.*`|`string`|`extract`|||
|`Borrowers.*.CurrentMonthlyRent`|`number`|`extract`|Borrower's monthly rent (if applicable)|1600|
|`Borrowers.*.SignedDate`|`date`|`extract`|Borrower's signature date|2021-03-16|
|`Borrowers.*.CoBorrowerSignedDate`|`date`|`extract`|Co-borrower's signature date|2021-03-16|
|`Borrowers.*.CurrentEmployment`|`object`|`generate`|Extracted borrower's current employment information||
|`Borrowers.*.CurrentEmployment.IsNotApplicable`|`boolean`|`extract`|Indicates if current employment section does not apply|false|
|`Borrowers.*.CurrentEmployment.EmployerName`|`string`|`extract`|Borrower's employer or business name|Spider Web Corp.|
|`Borrowers.*.CurrentEmployment.EmployerPhoneNumber`|`string`|`extract`|Borrower's employer phone number|(390) 353-2474|
|`Borrowers.*.CurrentEmployment.EmployerAddress`|`string`|`extract`|Borrower's employer address|3533 Bandini Ave<br>Glendale CA 92506 United States|
|`Borrowers.*.CurrentEmployment.PositionOrTitle`|`string`|`extract`|Borrower's position or title|Language Teacher|
|`Borrowers.*.CurrentEmployment.StartDate`|`date`|`extract`|Borrower's employment start date|2020-01-08|
|`Borrowers.*.CurrentEmployment.GrossMonthlyIncomeTotal`|`number`|`extract`|Borrower's gross monthly income total|4254|
|`Borrowers.*.Signature`|`string`|`classify`|Borrower's signature presence classification|signed|
|`Borrowers.*.CoBorrowerSignature`|`string`|`classify`|Co-borrower's signature presence classification|signed|
|`Loan`|`object`|`generate`|Extracted loan information||
|`Loan.Amount`|`number`|`extract`|Loan amount|156000|
|`Loan.PurposeType`|`array`|`generate`|Loan purpose selection(s)||
|`Loan.PurposeType.*`|`string`|`extract`|||
|`Loan.OtherPurpose`|`string`|`extract`|Other loan purpose type (if provided)|Construction|
|`Loan.RefinanceType`|`array`|`generate`|Loan refinance type selection(s)||
|`Loan.RefinanceType.*`|`string`|`extract`|||
|`Loan.RefinanceProgramType`|`array`|`generate`|Loan refinance program selection(s)||
|`Loan.RefinanceProgramType.*`|`string`|`extract`|||
|`Loan.OtherRefinanceProgram`|`string`|`extract`|Other loan refinance program type (if provided)|Streamlined without Appraisal|
|`Property`|`object`|`generate`|Extracted property information||
|`Property.Address`|`string`|`extract`|Property address|1634 W Glenoaks Blvd<br>Glendale CA 91201|
|`Property.NumberOfUnits`|`integer`|`extract`|Number of units|1|
|`Property.Value`|`number`|`extract`|Property value|200000|
|`Property.OccupancyStatus`|`array`|`generate`|Property occupancy status selection(s)||
|`Property.OccupancyStatus.*`|`string`|`extract`|||
|`Property.IsFHASecondaryResidence`|`boolean`|`extract`|Indicates FHA secondary residence|false|
|`Property.MixedUseProperty`|`array`|`generate`|Mixed-use property selection (Yes/No)||
|`Property.MixedUseProperty.*`|`string`|`extract`|||
|`Property.ManufacturedHome`|`array`|`generate`|Manufactured home selection (Yes/No)||
|`Property.ManufacturedHome.*`|`string`|`extract`|||
