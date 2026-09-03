**Analyzer ID:** `prebuilt-tax.us.1040Schedule3.2025`

**Description:** Extract tax US 1040 schedule3 document fields of 2025 form.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-Schedule3.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`Box1`|`number`|`extract`|Box 1 extracted from Form 1040-Schedule3.|654|
|`Box2`|`number`|`extract`|Box 2 extracted from Form 1040-Schedule3.|951|
|`Box3`|`number`|`extract`|Box 3 extracted from Form 1040-Schedule3.|753|
|`Box4`|`number`|`extract`|Box 4 extracted from Form 1040-Schedule3.|123|
|`Box5a`|`number`|`extract`|Box 5a extracted from Form 1040-Schedule3.|321|
|`Box5b`|`number`|`extract`|Box 5b extracted from Form 1040-Schedule3.|987|
|`Box6a`|`number`|`extract`|Box 6a extracted from Form 1040-Schedule3.|852|
|`Box6b`|`number`|`extract`|Box 6b extracted from Form 1040-Schedule3.|963|
|`Box6c`|`number`|`extract`|Box 6c extracted from Form 1040-Schedule3.|741|
|`Box6d`|`number`|`extract`|Box 6d extracted from Form 1040-Schedule3.|126|
|`Box6f`|`number`|`extract`|Box 6f extracted from Form 1040-Schedule3.|986|
|`Box6g`|`number`|`extract`|Box 6g extracted from Form 1040-Schedule3.|341|
|`Box6h`|`number`|`extract`|Box 6h extracted from Form 1040-Schedule3.|129|
|`Box6i`|`number`|`extract`|Box 6i extracted from Form 1040-Schedule3.|985|
|`Box6j`|`number`|`extract`|Box 6j extracted from Form 1040-Schedule3.|167|
|`Box6k`|`number`|`extract`|Box 6k extracted from Form 1040-Schedule3.|987.12|
|`Box6l`|`number`|`extract`|Box 6l extracted from Form 1040-Schedule3.|213|
|`Box6m`|`number`|`extract`|Box 6m extracted from Form 1040-Schedule3.|846|
|`Box6zExtraInfo`|`string`|`extract`|Box 6z extra info (type/description).|Credit for child and dependent care expenses|
|`Box6z`|`number`|`extract`|Box 6z amount extracted from Form 1040-Schedule3.|963|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-Schedule3 (total other nonrefundable credits).|123|
|`Box8`|`number`|`extract`|Box 8 extracted from Form 1040-Schedule3.|974|
|`Box9`|`number`|`extract`|Box 9 extracted from Form 1040-Schedule3.|984|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-Schedule3.|215|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-Schedule3.|321|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-Schedule3.|215|
|`Box13a`|`number`|`extract`|Box 13a extracted from Form 1040-Schedule3.|852|
|`Box13b`|`number`|`extract`|Box 13b extracted from Form 1040-Schedule3.|354|
|`Box13c`|`number`|`extract`|Box 13c extracted from Form 1040-Schedule3.|156|
|`Box13d`|`number`|`extract`|Box 13d extracted from Form 1040-Schedule3.|216|
|`Box13zExtraInfo`|`string`|`extract`|Box 13z extra info (type/description).|Net premium tax credit|
|`Box13z`|`number`|`extract`|Box 13z amount extracted from Form 1040-Schedule3.|123|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-Schedule3 (total other payments or refundable credits).|9512|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-Schedule3.|98745|
