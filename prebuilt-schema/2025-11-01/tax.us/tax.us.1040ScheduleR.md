| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleR.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Smith|
|`Part1`|`array`|`generate`|Part I filing status and age selection(s).||
|`Part1.*`|`string`|`extract`|||
|`Part2IsChecked`|`boolean`|`extract`|Part II disability statement checkbox.|true|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-ScheduleR.|123456|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-ScheduleR.|123456|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-ScheduleR.|123456|
|`Box13a`|`number`|`extract`|Box 13a extracted from Form 1040-ScheduleR.|123456|
|`Box13b`|`number`|`extract`|Box 13b extracted from Form 1040-ScheduleR.|123456|
|`Box13c`|`number`|`extract`|Box 13c extracted from Form 1040-ScheduleR.|123456|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-ScheduleR.|123456|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-ScheduleR.|123456|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-ScheduleR.|123456|
|`Box17`|`number`|`extract`|Box 17 extracted from Form 1040-ScheduleR.|123456|
|`Box18`|`number`|`extract`|Box 18 extracted from Form 1040-ScheduleR.|123456|
|`Box19`|`number`|`extract`|Box 19 extracted from Form 1040-ScheduleR.|123456|
|`Box20`|`number`|`extract`|Box 20 extracted from Form 1040-ScheduleR.|123456|
|`Box21`|`number`|`extract`|Box 21 extracted from Form 1040-ScheduleR.|123456|
|`Box22`|`number`|`extract`|Box 22 extracted from Form 1040-ScheduleR.|123456|
