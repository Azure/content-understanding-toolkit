**Analyzer ID:** `prebuilt-tax.us.1040Schedule8812.2025`

**Description:** Extract tax US 1040 schedule8812 document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-Schedule8812.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`Box1`|`number`|`extract`|Box 1 extracted from Schedule 8812.|195000|
|`Box2a`|`number`|`extract`|Box 2a extracted from Schedule 8812.|3500|
|`Box2b`|`number`|`extract`|Box 2b extracted from Schedule 8812.|1800|
|`Box2c`|`number`|`extract`|Box 2c extracted from Schedule 8812.|1200|
|`Box2d`|`number`|`extract`|Box 2d extracted from Schedule 8812.|6500|
|`Box3`|`number`|`extract`|Box 3 extracted from Schedule 8812.|201500|
|`Box4`|`integer`|`extract`|Box 4 extracted from Schedule 8812 (number of qualifying children under age 17).|1|
|`Box5`|`number`|`extract`|Box 5 extracted from Schedule 8812.|2000|
|`Box6`|`integer`|`extract`|Box 6 extracted from Schedule 8812 (number of other dependents).|2|
|`Box7`|`number`|`extract`|Box 7 extracted from Schedule 8812.|1000|
|`Box8`|`number`|`extract`|Box 8 extracted from Schedule 8812.|3000|
|`Box9`|`number`|`extract`|Box 9 extracted from Schedule 8812 (threshold by filing status).|200000|
|`Box10`|`number`|`extract`|Box 10 extracted from Schedule 8812.|2000|
|`Box11`|`number`|`extract`|Box 11 extracted from Schedule 8812.|100|
|`Box12ExtraInfo`|`array`|`generate`|Line 12 yes/no selection.||
|`Box12ExtraInfo.*`|`string`|`extract`||Yes|
|`Box12`|`number`|`extract`|Box 12 value (line 8 minus line 11).|2900|
|`Box13`|`number`|`extract`|Box 13 extracted from Schedule 8812 (Credit Limit Worksheet A).|6000|
|`Box14`|`number`|`extract`|Box 14 extracted from Schedule 8812 (CTC and ODC).|2900|
|`Box15`|`boolean`|`extract`|Line 15 checkbox (do not claim additional child tax credit).|false|
|`Box16a`|`number`|`extract`|Box 16a extracted from Schedule 8812 (line 12 minus line 14).|400|
|`Box16bExtraInfo`|`integer`|`extract`|Number of qualifying children under 17 with SSN used in line 16b multiplication.|1|
|`Box16b`|`number`|`extract`|Box 16b extracted from Schedule 8812 (result of count x 1,600).|1600|
|`Box17`|`number`|`extract`|Box 17 extracted from Schedule 8812 (smaller of 16a or 16b).|400|
|`Box18a`|`number`|`extract`|Box 18a extracted from Schedule 8812 (earned income).|190000|
|`Box18b`|`number`|`extract`|Box 18b extracted from Schedule 8812 (nontaxable combat pay).|0|
|`Box19ExtraInfo`|`array`|`generate`|Line 19 yes/no selection.||
|`Box19ExtraInfo.*`|`string`|`extract`||Yes|
|`Box19`|`number`|`extract`|Box 19 extracted from Schedule 8812 (earned income minus 2,500, if > 0).|187500|
|`Box20`|`number`|`extract`|Box 20 extracted from Schedule 8812 (15% of line 19).|28125|
|`Box20ExtraInfo`|`array`|`generate`|Next-step yes/no selection related to line 20 vs line 17 or Puerto Rico residency.||
|`Box20ExtraInfo.*`|`string`|`extract`||No|
|`Box21`|`number`|`extract`|Box 21 extracted from Schedule 8812.|13200|
|`Box22`|`number`|`extract`|Box 22 extracted from Schedule 8812.|2800|
|`Box23`|`number`|`extract`|Box 23 extracted from Schedule 8812.|16000|
|`Box24`|`number`|`extract`|Box 24 extracted from Schedule 8812.|4200|
|`Box25`|`number`|`extract`|Box 25 extracted from Schedule 8812.|11800|
|`Box26`|`number`|`extract`|Box 26 extracted from Schedule 8812.|28125|
|`Box27`|`number`|`extract`|Box 27 extracted from Schedule 8812 (additional child tax credit).|400|
