**Analyzer ID:** `prebuilt-tax.us.1040ScheduleEIC.2025`

**Description:** Extract tax US 1040 schedule eic document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleEIC.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer tax social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`IsSeparatedAndMeetingEICClaimRequirements`|`boolean`|`extract`|Separated from spouse, filing a separate return, and meeting EIC claim requirements (checkbox).|true|
|`QualifyingChildInformation`|`array`|`generate`|Qualifying child information extracted from Form 1040-ScheduleEIC.||
|`QualifyingChildInformation.*`|`object`|`generate`|||
|`QualifyingChildInformation.*.Name`|`string`|`extract`|Child's name.|Bob Weydert|
|`QualifyingChildInformation.*.SSN`|`string`|`extract`|Child's SSN (or 'Died' when applicable).|321-54-9876|
|`QualifyingChildInformation.*.BirthYear`|`string`|`extract`|Child's year of birth (YYYY).|1990|
|`QualifyingChildInformation.*.Under24`|`array`|`generate`|Was the child under age 24 at the end of the year, a student, and younger than you (Yes/No).||
|`QualifyingChildInformation.*.Under24.*`|`string`|`extract`|||
|`QualifyingChildInformation.*.PermanentlyDisabled`|`array`|`generate`|Was the child permanently and totally disabled during any part of the year? (Yes/No).||
|`QualifyingChildInformation.*.PermanentlyDisabled.*`|`string`|`extract`|||
|`QualifyingChildInformation.*.RelationshipToTaxpayer`|`string`|`extract`|Child's relationship to the taxpayer.|Son|
|`QualifyingChildInformation.*.NumberOfMonthsLivedWithTaxpayer`|`integer`|`extract`|Number of months the child lived with the taxpayer in the U.S. during the year.|12|
