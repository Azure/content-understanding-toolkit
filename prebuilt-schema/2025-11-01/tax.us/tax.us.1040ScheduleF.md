**Analyzer ID:** `prebuilt-tax.us.1040ScheduleF`

**Description:** Profit or Loss from Farming.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleF.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Smith|
|`BoxA`|`string`|`extract`|Box A extracted from Form 1040-ScheduleF.|Wheat|
|`BoxB`|`string`|`extract`|Box B extracted from Form 1040-ScheduleF.|123456|
|`BoxC`|`array`|`generate`|Accounting method selections (e.g., Cash, Accrual).||
|`BoxC.*`|`string`|`extract`|||
|`BoxD`|`string`|`extract`|Box D extracted from Form 1040-ScheduleF.|12-3456789|
|`BoxE`|`array`|`generate`|Material participation question (Yes/No).||
|`BoxE.*`|`string`|`extract`|||
|`BoxF`|`array`|`generate`|Payments requiring Form(s) 1099? (Yes/No).||
|`BoxF.*`|`string`|`extract`|||
|`BoxG`|`array`|`generate`|If Yes, did/will you file required 1099s? (Yes/No).||
|`BoxG.*`|`string`|`extract`|||
|`Box1a`|`number`|`extract`|Box 1a extracted from Form 1040-ScheduleF.|123456|
|`Box1b`|`number`|`extract`|Box 1b extracted from Form 1040-ScheduleF.|123456|
|`Box1c`|`number`|`extract`|Box 1c extracted from Form 1040-ScheduleF.|123456|
|`Box2`|`number`|`extract`|Box 2 extracted from Form 1040-ScheduleF.|123456|
|`Box3a`|`number`|`extract`|Box 3a extracted from Form 1040-ScheduleF.|123456|
|`Box3b`|`number`|`extract`|Box 3b extracted from Form 1040-ScheduleF.|123456|
|`Box4a`|`number`|`extract`|Box 4a extracted from Form 1040-ScheduleF.|123456|
|`Box4b`|`number`|`extract`|Box 4b extracted from Form 1040-ScheduleF.|123456|
|`Box5a`|`number`|`extract`|Box 5a extracted from Form 1040-ScheduleF.|123456|
|`Box5b`|`number`|`extract`|Box 5b extracted from Form 1040-ScheduleF.|123456|
|`Box5c`|`number`|`extract`|Box 5c extracted from Form 1040-ScheduleF.|123456|
|`Box6a`|`number`|`extract`|Box 6a extracted from Form 1040-ScheduleF.|123456|
|`Box6b`|`number`|`extract`|Box 6b extracted from Form 1040-ScheduleF.|123456|
|`Box6cIsChecked`|`boolean`|`extract`|Box 6c checkbox (election to defer is attached).|true|
|`Box6d`|`number`|`extract`|Box 6d extracted from Form 1040-ScheduleF.|123456|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-ScheduleF.|123456|
|`Box8`|`number`|`extract`|Box 8 extracted from Form 1040-ScheduleF.|123456|
|`Box9`|`number`|`extract`|Box 9 extracted from Form 1040-ScheduleF.|123456|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-ScheduleF.|123456|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-ScheduleF.|123456|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-ScheduleF.|123456|
|`Box13`|`number`|`extract`|Box 13 extracted from Form 1040-ScheduleF.|123456|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-ScheduleF.|123456|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-ScheduleF.|123456|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-ScheduleF.|123456|
|`Box17`|`number`|`extract`|Box 17 extracted from Form 1040-ScheduleF.|123456|
|`Box18`|`number`|`extract`|Box 18 extracted from Form 1040-ScheduleF.|123456|
|`Box19`|`number`|`extract`|Box 19 extracted from Form 1040-ScheduleF.|123456|
|`Box20`|`number`|`extract`|Box 20 extracted from Form 1040-ScheduleF.|123456|
|`Box21a`|`number`|`extract`|Box 21a extracted from Form 1040-ScheduleF.|123456|
|`Box21b`|`number`|`extract`|Box 21b extracted from Form 1040-ScheduleF.|123456|
|`Box22`|`number`|`extract`|Box 22 extracted from Form 1040-ScheduleF.|123456|
|`Box23`|`number`|`extract`|Box 23 extracted from Form 1040-ScheduleF.|123456|
|`Box24a`|`number`|`extract`|Box 24a extracted from Form 1040-ScheduleF.|123456|
|`Box24b`|`number`|`extract`|Box 24b extracted from Form 1040-ScheduleF.|123456|
|`Box25`|`number`|`extract`|Box 25 extracted from Form 1040-ScheduleF.|123456|
|`Box26`|`number`|`extract`|Box 26 extracted from Form 1040-ScheduleF.|123456|
|`Box27`|`number`|`extract`|Box 27 extracted from Form 1040-ScheduleF.|123456|
|`Box28`|`number`|`extract`|Box 28 extracted from Form 1040-ScheduleF.|123456|
|`Box29`|`number`|`extract`|Box 29 extracted from Form 1040-ScheduleF.|123456|
|`Box30`|`number`|`extract`|Box 30 extracted from Form 1040-ScheduleF.|123456|
|`Box31`|`number`|`extract`|Box 31 extracted from Form 1040-ScheduleF.|123456|
|`Box32aExtraInfo`|`string`|`extract`|Box 32a extra info extracted from Form 1040-ScheduleF.|Landscaping|
|`Box32a`|`number`|`extract`|Box 32a extracted from Form 1040-ScheduleF.|123456|
|`Box32bExtraInfo`|`string`|`extract`|Box 32b extra info extracted from Form 1040-ScheduleF.|Landscaping|
|`Box32b`|`number`|`extract`|Box 32b extracted from Form 1040-ScheduleF.|123456|
|`Box32cExtraInfo`|`string`|`extract`|Box 32c extra info extracted from Form 1040-ScheduleF.|Landscaping|
|`Box32c`|`number`|`extract`|Box 32c extracted from Form 1040-ScheduleF.|123456|
|`Box32dExtraInfo`|`string`|`extract`|Box 32d extra info extracted from Form 1040-ScheduleF.|Landscaping|
|`Box32d`|`number`|`extract`|Box 32d extracted from Form 1040-ScheduleF.|123456|
|`Box32eExtraInfo`|`string`|`extract`|Box 32e extra info extracted from Form 1040-ScheduleF.|Landscaping|
|`Box32e`|`number`|`extract`|Box 32e extracted from Form 1040-ScheduleF.|123456|
|`Box32fExtraInfo`|`string`|`extract`|Box 32f extra info extracted from Form 1040-ScheduleF.|Landscaping|
|`Box32f`|`number`|`extract`|Box 32f extracted from Form 1040-ScheduleF.|123456|
|`Box33`|`number`|`extract`|Box 33 extracted from Form 1040-ScheduleF.|123456|
|`Box34`|`number`|`extract`|Box 34 extracted from Form 1040-ScheduleF.|123456|
|`Box36`|`array`|`generate`|Investment at risk selection.||
|`Box36.*`|`string`|`extract`|||
|`Box37`|`number`|`extract`|Box 37 extracted from Form 1040-ScheduleF.|123456|
|`Box38a`|`number`|`extract`|Box 38a extracted from Form 1040-ScheduleF.|123456|
|`Box38b`|`number`|`extract`|Box 38b extracted from Form 1040-ScheduleF.|123456|
|`Box39a`|`number`|`extract`|Box 39a extracted from Form 1040-ScheduleF.|123456|
|`Box39b`|`number`|`extract`|Box 39b extracted from Form 1040-ScheduleF.|123456|
|`Box40a`|`number`|`extract`|Box 40a extracted from Form 1040-ScheduleF.|123456|
|`Box40b`|`number`|`extract`|Box 40b extracted from Form 1040-ScheduleF.|123456|
|`Box40c`|`number`|`extract`|Box 40c extracted from Form 1040-ScheduleF.|123456|
|`Box41`|`number`|`extract`|Box 41 extracted from Form 1040-ScheduleF.|123456|
|`Box42`|`number`|`extract`|Box 42 extracted from Form 1040-ScheduleF.|123456|
|`Box43`|`number`|`extract`|Box 43 extracted from Form 1040-ScheduleF.|123456|
|`Box44`|`number`|`extract`|Box 44 extracted from Form 1040-ScheduleF.|123456|
|`Box45`|`number`|`extract`|Box 45 extracted from Form 1040-ScheduleF.|123456|
|`Box46`|`number`|`extract`|Box 46 extracted from Form 1040-ScheduleF.|123456|
|`Box47`|`number`|`extract`|Box 47 extracted from Form 1040-ScheduleF.|123456|
|`Box48`|`number`|`extract`|Box 48 extracted from Form 1040-ScheduleF.|123456|
|`Box49`|`number`|`extract`|Box 49 extracted from Form 1040-ScheduleF.|123456|
|`Box50`|`number`|`extract`|Box 50 extracted from Form 1040-ScheduleF.|123456|
