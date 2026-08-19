| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleH.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Smith|
|`PaidPreparer`|`object`|`generate`|||
|`PaidPreparer.Name`|`string`|`extract`|Preparer name.|John Smith|
|`PaidPreparer.PTIN`|`string`|`extract`|Preparer PTIN.|P12345678|
|`PaidPreparer.IsPreparerSelfEmployed`|`boolean`|`extract`|Is preparer self-employed.|true|
|`PaidPreparer.FirmName`|`string`|`extract`|Preparer firm name.|Contoso LLC|
|`PaidPreparer.FirmPhoneNumber`|`string`|`extract`|Preparer's firm phone number.|1-123-456-7890|
|`PaidPreparer.FirmAddress`|`string`|`extract`|Preparer firm address.|123 First Street, Seattle WA 98001|
|`PaidPreparer.FirmEIN`|`string`|`extract`|Preparer firm EIN.|98-7654321|
|`EIN`|`string`|`extract`|Employer identification number.|12-3456789|
|`BoxA`|`array`|`generate`|Line A Yes/No selection.||
|`BoxA.*`|`string`|`extract`|||
|`BoxB`|`array`|`generate`|Line B Yes/No selection.||
|`BoxB.*`|`string`|`extract`|||
|`BoxC`|`array`|`generate`|Line C Yes/No selection.||
|`BoxC.*`|`string`|`extract`|||
|`Box1`|`number`|`extract`|Box 1 extracted from Form 1040-ScheduleH.|123456|
|`Box2`|`number`|`extract`|Box 2 extracted from Form 1040-ScheduleH.|123456|
|`Box3`|`number`|`extract`|Box 3 extracted from Form 1040-ScheduleH.|123456|
|`Box4`|`number`|`extract`|Box 4 extracted from Form 1040-ScheduleH.|123456|
|`Box5`|`number`|`extract`|Box 5 extracted from Form 1040-ScheduleH.|123456|
|`Box6`|`number`|`extract`|Box 6 extracted from Form 1040-ScheduleH.|123456|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-ScheduleH.|123456|
|`Box8`|`number`|`extract`|Box 8 extracted from Form 1040-ScheduleH.|123456|
|`Box9`|`array`|`generate`|Line 9 Yes/No selection.||
|`Box9.*`|`string`|`extract`|||
|`Box10`|`array`|`generate`|Line 10 Yes/No selection.||
|`Box10.*`|`string`|`extract`|||
|`Box11`|`array`|`generate`|Line 11 Yes/No selection.||
|`Box11.*`|`string`|`extract`|||
|`Box12`|`array`|`generate`|Line 12 Yes/No selection.||
|`Box12.*`|`string`|`extract`|||
|`Box13`|`string`|`extract`|Box 13 extracted from Form 1040-ScheduleH.|Washington|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-ScheduleH.|123456|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-ScheduleH.|123456|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-ScheduleH.|123456|
|`Box18g`|`number`|`extract`|Box 18g extracted from Form 1040-ScheduleH.|123456|
|`Box18h`|`number`|`extract`|Box 18h extracted from Form 1040-ScheduleH.|123456|
|`Box19`|`number`|`extract`|Box 19 extracted from Form 1040-ScheduleH.|123456|
|`Box20`|`number`|`extract`|Box 20 extracted from Form 1040-ScheduleH.|123456|
|`Box21`|`number`|`extract`|Box 21 extracted from Form 1040-ScheduleH.|123456|
|`Box22`|`number`|`extract`|Box 22 extracted from Form 1040-ScheduleH.|123456|
|`Box23IsChecked`|`boolean`|`extract`|Box 23 checkbox (credit reduction/late state contributions indicator).|true|
|`Box23`|`number`|`extract`|Box 23 extracted from Form 1040-ScheduleH.|123456|
|`Box24`|`number`|`extract`|Box 24 extracted from Form 1040-ScheduleH.|123456|
|`Box25`|`number`|`extract`|Box 25 extracted from Form 1040-ScheduleH.|123456|
|`Box26`|`number`|`extract`|Box 26 extracted from Form 1040-ScheduleH.|123456|
|`Box27`|`array`|`generate`|Line 27 Yes/No selection.||
|`Box27.*`|`string`|`extract`|||
|`TaxpayerAddress`|`string`|`extract`|Taxpayer address extracted from Form 1040-ScheduleH.|123 Microsoft Way, Redmond WA 98052|
|`Box17`|`array`|`generate`|State-specific FUTA details extracted from Form 1040-ScheduleH.||
|`Box17.*`|`object`|`generate`|||
|`Box17.*.NameOfState`|`string`|`extract`|Name of state.|WA|
|`Box17.*.TaxableWage`|`number`|`extract`|Taxable wages (as defined in state act).|123456|
|`Box17.*.StateExperienceRatePeriodFromDate`|`date`|`extract`|State experience rate period start date.|2023-01-01|
|`Box17.*.StateExperienceRatePeriodToDate`|`date`|`extract`|State experience rate period end date.|2023-12-31|
|`Box17.*.StateExperienceRate`|`number`|`extract`|State experience rate.|0.50|
|`Box17.*.BoxE`|`number`|`extract`|Column (e): Multiply col. (b) by 0.054.|123456|
|`Box17.*.BoxF`|`number`|`extract`|Column (f): Multiply col. (b) by col. (d).|123456|
|`Box17.*.BoxG`|`number`|`extract`|Column (g): Subtract col. (f) from col. (e).|123456|
|`Box17.*.ContributionPaid`|`number`|`extract`|Contributions paid to state unemployment fund (column h).|123456|
