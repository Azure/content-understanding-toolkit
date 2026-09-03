**Analyzer ID:** `prebuilt-tax.us.1040Schedule2`

**Description:** Additional Taxes.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-Schedule2.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`Box1a`|`number`|`extract`|Box 1a extracted from Form 1040-Schedule2.|1350|
|`Box1b`|`number`|`extract`|Box 1b extracted from Form 1040-Schedule2.|2000|
|`Box1c`|`number`|`extract`|Box 1c extracted from Form 1040-Schedule2.|1200|
|`Box1d`|`number`|`extract`|Box 1d extracted from Form 1040-Schedule2.|450|
|`Box1e`|`number`|`extract`|Box 1e extracted from Form 1040-Schedule2.|175|
|`Box1eApplicableBox`|`array`|`generate`|Box 1e applicable box selection(s).||
|`Box1eApplicableBox.*`|`string`|`extract`||Line 1c|
|`Box1f`|`number`|`extract`|Box 1f extracted from Form 1040-Schedule2.|90|
|`Box1fApplicableBox`|`array`|`generate`|Box 1f applicable box selection(s).||
|`Box1fApplicableBox.*`|`string`|`extract`||Line 1d|
|`Box1y`|`number`|`extract`|Box 1y extracted from Form 1040-Schedule2.|135|
|`Box1yExtraInfo`|`string`|`extract`|Box 1y extra info (type/description).|Penalties for underpayment|
|`Box1z`|`number`|`extract`|Box 1z extracted from Form 1040-Schedule2.||
|`Box2`|`number`|`extract`|Box 2 extracted from Form 1040-Schedule2.|987|
|`Box3`|`number`|`extract`|Box 3 extracted from Form 1040-Schedule2.|125|
|`Box4`|`number`|`extract`|Box 4 extracted from Form 1040-Schedule2.|987|
|`Box4FromForm`|`array`|`generate`|Box 4 source form information.||
|`Box4FromForm.*`|`string`|`extract`||4361|
|`Box4OtherFormNumber`|`string`|`extract`|Box 4 other form number if applicable.||
|`Box5`|`number`|`extract`|Box 5 extracted from Form 1040-Schedule2.|124|
|`Box6`|`number`|`extract`|Box 6 extracted from Form 1040-Schedule2.|125|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-Schedule2.|841|
|`Box8IsChecked`|`boolean`|`extract`|Box 8 checkbox (not required to attach Form 5329).|true|
|`Box8`|`number`|`extract`|Box 8 extracted from Form 1040-Schedule2.|843|
|`Box9`|`number`|`extract`|Box 9 extracted from Form 1040-Schedule2.|547|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-Schedule2.|127123|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-Schedule2.|458|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-Schedule2.|123|
|`Box13`|`number`|`extract`|Box 13 extracted from Form 1040-Schedule2.|894|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-Schedule2.|888|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-Schedule2.|123|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-Schedule2.|984.23|
|`Box17aExtraInfo`|`string`|`extract`|Box 17a extra info (type/form number).|8936R|
|`Box17a`|`number`|`extract`|Box 17a extracted from Form 1040-Schedule2.|28542|
|`Box17b`|`number`|`extract`|Box 17b extracted from Form 1040-Schedule2.|325|
|`Box17c`|`number`|`extract`|Box 17c extracted from Form 1040-Schedule2.|146|
|`Box17d`|`number`|`extract`|Box 17d extracted from Form 1040-Schedule2.|987|
|`Box17e`|`number`|`extract`|Box 17e extracted from Form 1040-Schedule2.|123|
|`Box17f`|`number`|`extract`|Box 17f extracted from Form 1040-Schedule2.|974|
|`Box17g`|`number`|`extract`|Box 17g extracted from Form 1040-Schedule2.|963|
|`Box17h`|`number`|`extract`|Box 17h extracted from Form 1040-Schedule2.|258|
|`Box17i`|`number`|`extract`|Box 17i extracted from Form 1040-Schedule2.|147|
|`Box17j`|`number`|`extract`|Box 17j extracted from Form 1040-Schedule2.|145|
|`Box17k`|`number`|`extract`|Box 17k extracted from Form 1040-Schedule2.|741|
|`Box17l`|`number`|`extract`|Box 17l extracted from Form 1040-Schedule2.|852|
|`Box17m`|`number`|`extract`|Box 17m extracted from Form 1040-Schedule2.|951|
|`Box17n`|`number`|`extract`|Box 17n extracted from Form 1040-Schedule2.|753|
|`Box17o`|`number`|`extract`|Box 17o extracted from Form 1040-Schedule2.|159|
|`Box17p`|`number`|`extract`|Box 17p extracted from Form 1040-Schedule2.|126|
|`Box17q`|`number`|`extract`|Box 17q extracted from Form 1040-Schedule2.|852|
|`Box17zExtraInfo`|`string`|`extract`|Box 17z extra info (type/description).|Council Tax|
|`Box17z`|`number`|`extract`|Box 17z amount extracted from Form 1040-Schedule2.|654|
|`Box18`|`number`|`extract`|Box 18 extracted from Form 1040-Schedule2 (total additional taxes).|123156|
|`Box19`|`number`|`extract`|Box 19 extracted from Form 1040-Schedule2 (reserved for future use).|0|
|`Box20`|`number`|`extract`|Box 20 extracted from Form 1040-Schedule2.|325|
|`Box21`|`number`|`extract`|Box 21 extracted from Form 1040-Schedule2 (total other taxes).|956123.987|
