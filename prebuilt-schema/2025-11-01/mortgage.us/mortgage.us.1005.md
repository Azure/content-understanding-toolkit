**Analyzer ID:** `prebuilt-mortgage.us.1005`

**Description:** Verification of Employment.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`Employer`|`object`|`generate`|Employer details||
|`Employer.Name`|`string`|`extract`|Employer name|ABC Software Company|
|`Employer.Address`|`string`|`extract`|Employer address|123 Main Street, Seattle, WA 98111|
|`Employer.Signature`|`string`|`classify`|Employer's signature presence classification|signed|
|`Lender`|`object`|`generate`|Lender details||
|`Lender.Name`|`string`|`extract`|Lender name|XYZ Mortgage Company|
|`Lender.Address`|`string`|`extract`|Lender address|789 Avenue, New York, NY 10001|
|`Lender.Signature`|`string`|`classify`|Lender's signature presence classification|signed|
|`Applicant`|`object`|`generate`|Applicant details||
|`Applicant.Name`|`string`|`extract`|Applicant name|Richard Smith|
|`Applicant.Address`|`string`|`extract`|Applicant address|456 Bay Blvd, Sacramento, CA 94203|
|`Applicant.Signature`|`string`|`classify`|Applicant's signature presence classification|signed|
|`PresentEmployment`|`object`|`generate`|Extracted present employment information.||
|`PresentEmployment.Date`|`date`|`extract`|Date when current employment began|2018-08-25|
|`PresentEmployment.Position`|`string`|`extract`|Current position/title|Software Engineer|
|`PresentEmployment.CurrentGrossBasePay`|`number`|`extract`|Current gross base pay|154895|
|`PresentEmployment.CurrentGrossBasePayPeriod`|`array`|`generate`|Gross base pay period selection(s) (Annual, Monthly, Weekly, Hourly, Other)||
|`PresentEmployment.CurrentGrossBasePayPeriod.*`|`string`|`extract`|||
|`PresentEmployment.OtherCurrentGrossBasePayPeriod`|`string`|`extract`|Description of other pay period, if applicable|Bi-Weekly|
|`PreviousEmployment`|`object`|`generate`|Extracted previous employment information.||
|`PreviousEmployment.DateHired`|`date`|`extract`|Date hired for previous job|2018-01-01|
|`PreviousEmployment.DateTerminated`|`date`|`extract`|Date employment was terminated|2020-10-30|
|`PreviousEmployment.PositionHeld`|`string`|`extract`|Position held at previous job|Supervisor|
