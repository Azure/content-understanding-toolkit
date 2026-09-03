**Analyzer ID:** `prebuilt-tax.us.1040Schedule1`

**Description:** Additional Income and Adjustments to Income.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-Schedule1.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`Form1099KAmountInError`|`number`|`extract`|Form 1099-K Amount in Error extracted from Form 1040-Schedule1.|1500|
|`Box1`|`number`|`extract`|Box 1 extracted from Form 1040-Schedule1.|321|
|`Box2a`|`number`|`extract`|Box 2a extracted from Form 1040-Schedule1.|963|
|`Box2b`|`date`|`extract`|Date of original divorce or separation agreement (2b).|2020-01-09|
|`Box3`|`number`|`extract`|Box 3 extracted from Form 1040-Schedule1.|321|
|`Box4`|`number`|`extract`|Box 4 extracted from Form 1040-Schedule1.|147|
|`Box4FromForm`|`array`|`generate`|Forms contributing to box 4.||
|`Box4FromForm.*`|`string`|`extract`||4797|
|`Box5`|`number`|`extract`|Box 5 extracted from Form 1040-Schedule1.|963|
|`Box6`|`number`|`extract`|Box 6 extracted from Form 1040-Schedule1.|852|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-Schedule1.|159|
|`Box7IsChecked`|`boolean`|`extract`|Box 7 checkbox indicator.|true|
|`Box7ExtraInfo`|`number`|`extract`|Box 7 extra info (type/description).||
|`Box8a`|`number`|`extract`|Box 8a extracted from Form 1040-Schedule1.|-987|
|`Box8b`|`number`|`extract`|Box 8b extracted from Form 1040-Schedule1.|152|
|`Box8c`|`number`|`extract`|Box 8c extracted from Form 1040-Schedule1.|123|
|`Box8d`|`number`|`extract`|Box 8d extracted from Form 1040-Schedule1.|-985|
|`Box8e`|`number`|`extract`|Box 8e extracted from Form 1040-Schedule1.|951|
|`Box8f`|`number`|`extract`|Box 8f extracted from Form 1040-Schedule1.|123|
|`Box8g`|`number`|`extract`|Box 8g extracted from Form 1040-Schedule1.|184|
|`Box8h`|`number`|`extract`|Box 8h extracted from Form 1040-Schedule1.|965|
|`Box8i`|`number`|`extract`|Box 8i extracted from Form 1040-Schedule1.|456|
|`Box8j`|`number`|`extract`|Box 8j extracted from Form 1040-Schedule1.|156|
|`Box8k`|`number`|`extract`|Box 8k extracted from Form 1040-Schedule1.|861|
|`Box8l`|`number`|`extract`|Box 8l extracted from Form 1040-Schedule1.|862|
|`Box8m`|`number`|`extract`|Box 8m extracted from Form 1040-Schedule1.|489|
|`Box8n`|`number`|`extract`|Box 8n extracted from Form 1040-Schedule1.|894|
|`Box8o`|`number`|`extract`|Box 8o extracted from Form 1040-Schedule1.|123|
|`Box8p`|`number`|`extract`|Box 8p extracted from Form 1040-Schedule1.|987|
|`Box8q`|`number`|`extract`|Box 8q extracted from Form 1040-Schedule1.|123632|
|`Box8r`|`number`|`extract`|Box 8r extracted from Form 1040-Schedule1.|148|
|`Box8s`|`number`|`extract`|Box 8s extracted from Form 1040-Schedule1.|-698|
|`Box8t`|`number`|`extract`|Box 8t extracted from Form 1040-Schedule1.|159|
|`Box8u`|`number`|`extract`|Box 8u extracted from Form 1040-Schedule1.|741.85|
|`Box8v`|`number`|`extract`|Box 8v extracted from Form 1040-Schedule1.|741.85|
|`Box8zExtraInfo`|`string`|`extract`|Box 8z extra info (type/description).|Video Game Tournament prize money|
|`Box8z`|`number`|`extract`|Box 8z amount extracted from Form 1040-Schedule1.|98412|
|`Box9`|`number`|`extract`|Box 9 extracted from Form 1040-Schedule1 (total other income).|123852|
|`Box10`|`number`|`extract`|Box 10 extracted from Form 1040-Schedule1 (additional income total).|123856|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-Schedule1.|85|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-Schedule1.|123|
|`Box13`|`number`|`extract`|Box 13 extracted from Form 1040-Schedule1.|974|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-Schedule1.|446|
|`Box14IsChecked`|`boolean`|`extract`|Box 14 checkbox indicator.|true|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-Schedule1.|568|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-Schedule1.|965|
|`Box17`|`number`|`extract`|Box 17 extracted from Form 1040-Schedule1.|127|
|`Box18`|`number`|`extract`|Box 18 extracted from Form 1040-Schedule1.|974|
|`Box19a`|`number`|`extract`|Box 19a extracted from Form 1040-Schedule1.|417|
|`Box19b`|`string`|`extract`|Recipient's SSN (19b).|987-65-4321|
|`Box19c`|`date`|`extract`|Date of original divorce or separation agreement (19c).|2021-01-02|
|`Box20`|`number`|`extract`|Box 20 extracted from Form 1040-Schedule1.|654|
|`Box20IsChecked`|`boolean`|`extract`|Box 20 checkbox indicator.|true|
|`Box21`|`number`|`extract`|Box 21 extracted from Form 1040-Schedule1.|147|
|`Box23`|`number`|`extract`|Box 23 extracted from Form 1040-Schedule1.|963|
|`Box24a`|`number`|`extract`|Box 24a extracted from Form 1040-Schedule1.|521|
|`Box24b`|`number`|`extract`|Box 24b extracted from Form 1040-Schedule1.|823|
|`Box24c`|`number`|`extract`|Box 24c extracted from Form 1040-Schedule1.|123|
|`Box24d`|`number`|`extract`|Box 24d extracted from Form 1040-Schedule1.|975.20|
|`Box24e`|`number`|`extract`|Box 24e extracted from Form 1040-Schedule1.|213|
|`Box24f`|`number`|`extract`|Box 24f extracted from Form 1040-Schedule1.|593|
|`Box24g`|`number`|`extract`|Box 24g extracted from Form 1040-Schedule1.|156|
|`Box24h`|`number`|`extract`|Box 24h extracted from Form 1040-Schedule1.|249|
|`Box24i`|`number`|`extract`|Box 24i extracted from Form 1040-Schedule1.|246|
|`Box24j`|`number`|`extract`|Box 24j extracted from Form 1040-Schedule1.|746|
|`Box24k`|`number`|`extract`|Box 24k extracted from Form 1040-Schedule1.|168|
|`Box24zExtraInfo`|`string`|`extract`|Box 24z extra info (type/description).|Covid tax break|
|`Box24z`|`number`|`extract`|Box 24z amount extracted from Form 1040-Schedule1.|632|
|`Box25`|`number`|`extract`|Box 25 extracted from Form 1040-Schedule1 (total other adjustments).|963123|
|`Box26`|`number`|`extract`|Box 26 extracted from Form 1040-Schedule1 (total adjustments to income).|963741|
