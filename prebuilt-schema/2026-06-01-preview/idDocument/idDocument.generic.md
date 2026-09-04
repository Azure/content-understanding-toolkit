**Analyzer ID:** `prebuilt-idDocument.generic`

**Description:** Generic identification documents from various regions.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`CountryRegion`|`string`|`generate`|Country or region code|USA|
|`Region`|`string`|`generate`|State or province|Washington|
|`DocumentNumber`|`string`|`extract`|Driver license number|WDLABCD456DG|
|`DocumentDiscriminator`|`string`|`extract`|Driver license document discriminator|12645646464554646456464544|
|`FirstName`|`string`|`extract`|Given name and middle initial if applicable|LIAM R.|
|`LastName`|`string`|`extract`|Surname|TALBOT|
|`Address`|`string`|`extract`|Address|123 STREET ADDRESS YOUR CITY WA 99999-1234|
|`BirthDate`|`date`|`extract`|Date of birth|1958-01-06|
|`ExpirationDate`|`date`|`extract`|Date of expiration|2020-08-12|
|`IssueDate`|`date`|`extract`|Date of issue|2012-08-12|
|`EyeColor`|`string`|`extract`|Eye color|BLU|
|`HairColor`|`string`|`extract`|Hair color|BRO|
|`Height`|`string`|`extract`|Height|5'11"|
|`Weight`|`string`|`extract`|Weight|185LB|
|`Sex`|`string`|`extract`|Sex|M|
|`Endorsements`|`string`|`extract`|Endorsements|L|
|`Restrictions`|`string`|`extract`|Restrictions|B|
|`PersonalNumber`|`string`|`extract`|Personal Id. No.|A234567893|
|`PlaceOfBirth`|`string`|`extract`|Place of birth|MASSACHUSETTS, U.S.A.|
|`VehicleClass`|`string`|`extract`|Vehicle class|D|
|`Category`|`string`|`extract`|Permit category|DV2|
