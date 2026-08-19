| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`DocumentNumber`|`string`|`extract`|Passport number printed in the VIZ|340020013|
|`FirstName`|`string`|`extract`|Given name printed in the VIZ|JENNIFER|
|`MiddleName`|`string`|`extract`|Name between given name and surname printed in the VIZ|REYES|
|`LastName`|`string`|`extract`|Surname printed in the VIZ|BROOKS|
|`Aliases`|`array`|`generate`|||
|`Aliases.*`|`string`|`extract`|Also known as|MAY LIN|
|`BirthDate`|`date`|`extract`|Date of birth printed in the VIZ|1980-01-01|
|`ExpirationDate`|`date`|`extract`|Date of expiration printed in the VIZ|2019-05-05|
|`IssueDate`|`date`|`extract`|Date of issue printed in the VIZ|2014-05-06|
|`Sex`|`string`|`extract`|Sex printed in the VIZ|F|
|`CountryRegion`|`string`|`extract`|Issuing country or organization printed in the VIZ|USA|
|`DocumentType`|`string`|`extract`|Document type printed in the VIZ|P|
|`Nationality`|`string`|`extract`|Nationality printed in the VIZ|USA|
|`PlaceOfBirth`|`string`|`extract`|Place of birth printed in the VIZ|MASSACHUSETTS, U.S.A.|
|`PlaceOfIssue`|`string`|`extract`|Place of issue printed in the VIZ|LA PAZ|
|`IssuingAuthority`|`string`|`extract`|Issuing authority printed in the VIZ|United States Department of State|
|`PersonalNumber`|`string`|`extract`|Personal ID number printed in the VIZ|A234567893|
|`MachineReadableZone`|`string`|`extract`|Machine readable zone (MRZ)|P<USABROOKS<<JENNIFER<<<<<<<<<<<<<<<<<<<<<<< 3400200135USA8001014F1905054710000307<715816|
