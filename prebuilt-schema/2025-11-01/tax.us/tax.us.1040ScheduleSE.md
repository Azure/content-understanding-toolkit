**Analyzer ID:** `prebuilt-tax.us.1040ScheduleSE`

**Description:** Self-Employment Tax.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleSE.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Smith|
|`BoxA`|`boolean`|`extract`|Box A checkbox (minister/religious order/Christian Science practitioner with Form 4361 and other net earnings).|true|
|`Box1a`|`number`|`extract`|Box 1a extracted from Form 1040-ScheduleSE.|123456|
|`Box1b`|`number`|`extract`|Box 1b extracted from Form 1040-ScheduleSE.|123456|
|`Box2`|`number`|`extract`|Box 2 extracted from Form 1040-ScheduleSE.|123456|
|`Box3`|`number`|`extract`|Box 3 extracted from Form 1040-ScheduleSE.|123456|
|`Box4a`|`number`|`extract`|Box 4a extracted from Form 1040-ScheduleSE.|123456|
|`Box4b`|`number`|`extract`|Box 4b extracted from Form 1040-ScheduleSE.|123456|
|`Box4c`|`number`|`extract`|Box 4c extracted from Form 1040-ScheduleSE.|123456|
|`Box5a`|`number`|`extract`|Box 5a extracted from Form 1040-ScheduleSE.|123456|
|`Box5b`|`number`|`extract`|Box 5b extracted from Form 1040-ScheduleSE.|123456|
|`Box6`|`number`|`extract`|Box 6 extracted from Form 1040-ScheduleSE.|123456|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-ScheduleSE.|147000|
|`Box8a`|`number`|`extract`|Box 8a extracted from Form 1040-ScheduleSE.|123456|
|`Box8b`|`number`|`extract`|Box 8b extracted from Form 1040-ScheduleSE.|123456|
|`Box8c`|`number`|`extract`|Box 8c extracted from Form 1040-ScheduleSE.|123456|
|`Box8d`|`number`|`extract`|Box 8d extracted from Form 1040-ScheduleSE.|123456|
|`Box9`|`number`|`extract`|Box 9 extracted from Form 1040-ScheduleSE.|123456|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-ScheduleSE.|123456|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-ScheduleSE.|123456|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-ScheduleSE.|123456|
|`Box13`|`number`|`extract`|Box 13 extracted from Form 1040-ScheduleSE.|123456|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-ScheduleSE.|6040|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-ScheduleSE.|123456|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-ScheduleSE.|123456|
|`Box17`|`number`|`extract`|Box 17 extracted from Form 1040-ScheduleSE.|123456|
