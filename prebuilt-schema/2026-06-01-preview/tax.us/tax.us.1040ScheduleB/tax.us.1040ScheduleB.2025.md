**Analyzer ID:** `prebuilt-tax.us.1040ScheduleB.2025`

**Description:** Extract tax US 1040 schedule b document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleB.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer tax social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascal Weydert|
|`Box2`|`number`|`extract`|Box 2 extracted from Form 1040-ScheduleB.|963|
|`Box3`|`number`|`extract`|Box 3 extracted from Form 1040-ScheduleB.|123|
|`Box4`|`number`|`extract`|Box 4 extracted from Form 1040-ScheduleB.|127|
|`Box6`|`number`|`extract`|Box 6 extracted from Form 1040-ScheduleB.|963|
|`Box7a`|`array`|`generate`|At any time during the tax year, did you have a financial interest in or signature authority over a financial account located in a foreign country?||
|`Box7a.*`|`string`|`extract`|||
|`Box7FileF114Required`|`array`|`generate`|If "Yes," are you required to file FinCEN Form 114 (FBAR)?||
|`Box7FileF114Required.*`|`string`|`extract`|||
|`Box7b`|`string`|`extract`|Foreign country(-ies) where the financial account(s) is (are) located.|United Kingdom|
|`Box8`|`array`|`generate`|During the tax year, did you receive a distribution from, or were you the grantor of, or transferor to, a foreign trust?||
|`Box8.*`|`string`|`extract`|||
|`Box1`|`array`|`generate`|List of interest payers and equivalent amounts extracted from Form 1040-ScheduleB.||
|`Box1.*`|`object`|`generate`|||
|`Box1.*.PayerDetails`|`string`|`extract`|Payer details extracted from Form 1040-ScheduleB.|Contoso PLC|
|`Box1.*.Amount`|`number`|`extract`|Amount extracted from Form 1040-ScheduleB.|321.65|
|`Box5`|`array`|`generate`|List of dividend payers and equivalent amounts extracted from Form 1040-ScheduleB.||
|`Box5.*`|`object`|`generate`|||
|`Box5.*.PayerDetails`|`string`|`extract`|Payer details extracted from Form 1040-ScheduleB.|Little Contoso Inc|
|`Box5.*.Amount`|`number`|`extract`|Amount extracted from Form 1040-ScheduleB.|856|
