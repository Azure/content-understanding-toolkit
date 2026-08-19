| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleA.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer tax social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`Box1`|`number`|`extract`|Box 1 extracted from Form 1040-ScheduleA.|123|
|`Box2`|`number`|`extract`|Box 2 extracted from Form 1040-ScheduleA.|198|
|`Box3`|`number`|`extract`|Box 3 extracted from Form 1040-ScheduleA.|246|
|`Box4`|`number`|`extract`|Box 4 extracted from Form 1040-ScheduleA.|128|
|`Box5aIsChecked`|`boolean`|`extract`|Box 5a checkbox indicator (general sales tax election).|true|
|`Box5a`|`number`|`extract`|Box 5a extracted from Form 1040-ScheduleA.|596|
|`Box5b`|`number`|`extract`|Box 5b extracted from Form 1040-ScheduleA.|249|
|`Box5c`|`number`|`extract`|Box 5c extracted from Form 1040-ScheduleA.|158|
|`Box5d`|`number`|`extract`|Box 5d extracted from Form 1040-ScheduleA.|128|
|`Box5e`|`number`|`extract`|Box 5e extracted from Form 1040-ScheduleA.|488|
|`Box6ExtraInfo`|`string`|`extract`|Box 6 extra information (type of other taxes).|Sales Tax|
|`Box6`|`number`|`extract`|Box 6 extracted from Form 1040-ScheduleA.|0|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-ScheduleA.|112|
|`Box8IsChecked`|`boolean`|`extract`|Box 8 checkbox indicator (home mortgage interest limitation notice).|true|
|`Box8a`|`number`|`extract`|Box 8a extracted from Form 1040-ScheduleA.|156|
|`Box8b`|`number`|`extract`|Box 8b extracted from Form 1040-ScheduleA.|256000|
|`Box8bExtraInfo`|`string`|`extract`|Box 8b extra information (payee name, identifying number, and address).|123 45th Ave N Seattle WA 98123|
|`Box8c`|`number`|`extract`|Box 8c extracted from Form 1040-ScheduleA.|125|
|`Box8d`|`number`|`extract`|Box 8d extracted from Form 1040-ScheduleA.|0|
|`Box8e`|`number`|`extract`|Box 8e extracted from Form 1040-ScheduleA.|987|
|`Box9`|`number`|`extract`|Box 9 extracted from Form 1040-ScheduleA.|654|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-ScheduleA.|321|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-ScheduleA.|741|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-ScheduleA.|852|
|`Box13`|`number`|`extract`|Box 13 extracted from Form 1040-ScheduleA.|963|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-ScheduleA.|741|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-ScheduleA.|951|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-ScheduleA.|123|
|`Box16ExtraInfo`|`string`|`extract`|Box 16 extra information.|Gifts (123.00)|
|`Box17`|`number`|`extract`|Box 17 extracted from Form 1040-ScheduleA.|12654|
|`Box18IsChecked`|`boolean`|`extract`|Box 18 checkbox indicator.|true|
