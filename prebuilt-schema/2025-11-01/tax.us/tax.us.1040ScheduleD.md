**Analyzer ID:** `prebuilt-tax.us.1040ScheduleD`

**Description:** Capital Gains and Losses.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleD.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer tax social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`QualifiedInvestmentDisposition`|`array`|`generate`|Did you dispose of any investment(s) in a qualified opportunity fund during the tax year?||
|`QualifiedInvestmentDisposition.*`|`string`|`extract`|||
|`Box4`|`number`|`extract`|Box 4 extracted from Form 1040-ScheduleD.|1654|
|`Box5`|`number`|`extract`|Box 5 extracted from Form 1040-ScheduleD.|123|
|`Box6`|`number`|`extract`|Box 6 extracted from Form 1040-ScheduleD.|-159|
|`Box7`|`number`|`extract`|Box 7 extracted from Form 1040-ScheduleD.|215|
|`Box11`|`number`|`extract`|Box 11 extracted from Form 1040-ScheduleD.|189.22|
|`Box12`|`number`|`extract`|Box 12 extracted from Form 1040-ScheduleD.|333.11|
|`Box13`|`number`|`extract`|Box 13 extracted from Form 1040-ScheduleD.|123.89|
|`Box14`|`number`|`extract`|Box 14 extracted from Form 1040-ScheduleD.|-368.11|
|`Box15`|`number`|`extract`|Box 15 extracted from Form 1040-ScheduleD.|123.22|
|`Box16`|`number`|`extract`|Box 16 extracted from Form 1040-ScheduleD.|877.66|
|`Box17`|`array`|`generate`|Are lines 15 and 16 both gains? (Yes/No)||
|`Box17.*`|`string`|`extract`|||
|`Box18`|`number`|`extract`|Amount from the 28% Rate Gain Worksheet, if required.|54|
|`Box19`|`number`|`extract`|Amount from the Unrecaptured Section 1250 Gain Worksheet, if required.|218.22|
|`Box20`|`array`|`generate`|Are lines 18 and 19 both zero or blank and you are not filing Form 4952? (Yes/No)||
|`Box20.*`|`string`|`extract`|||
|`Box21`|`number`|`extract`|If line 16 is a loss, enter the smaller of the loss on line 16 or $3,000 ($1,500 if MFS).|-231|
|`Box22`|`array`|`generate`|Do you have qualified dividends on Form 1040 line 3a? (Yes/No)||
|`Box22.*`|`string`|`extract`|||
|`Box1a`|`object`|`generate`|Totals for all short-term transactions reported on Form 1099-B with no adjustments.||
|`Box1a.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|321|
|`Box1a.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|123|
|`Box1a.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|543|
|`Box1b`|`object`|`generate`|Totals for all transactions reported on Form(s) 8949 with Box A checked.||
|`Box1b.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|168|
|`Box1b.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|156|
|`Box1b.Adjustments`|`number`|`extract`|Adjustments extracted from Form 1040-ScheduleD.|158.33|
|`Box1b.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|987|
|`Box2`|`object`|`generate`|Totals for all transactions reported on Form(s) 8949 with Box B checked.||
|`Box2.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|126.21|
|`Box2.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|21|
|`Box2.Adjustments`|`number`|`extract`|Adjustments extracted from Form 1040-ScheduleD.|548.22|
|`Box2.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|398.01|
|`Box3`|`object`|`generate`|Totals for all transactions reported on Form(s) 8949 with Box C checked.||
|`Box3.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|169|
|`Box3.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|589|
|`Box3.Adjustments`|`number`|`extract`|Adjustments extracted from Form 1040-ScheduleD.|156.22|
|`Box3.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|54|
|`Box8a`|`object`|`generate`|Totals for all long-term transactions reported on Form 1099-B with no adjustments.||
|`Box8a.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|575|
|`Box8a.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|23|
|`Box8a.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|325|
|`Box8b`|`object`|`generate`|Totals for all transactions reported on Form(s) 8949 with Box D checked.||
|`Box8b.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|248|
|`Box8b.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|268|
|`Box8b.Adjustments`|`number`|`extract`|Adjustments extracted from Form 1040-ScheduleD.|441|
|`Box8b.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|125|
|`Box9`|`object`|`generate`|Totals for all transactions reported on Form(s) 8949 with Box E checked.||
|`Box9.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|159|
|`Box9.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|236|
|`Box9.Adjustments`|`number`|`extract`|Adjustments extracted from Form 1040-ScheduleD.|156|
|`Box9.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|189|
|`Box10`|`object`|`generate`|Totals for all transactions reported on Form(s) 8949 with Box F checked.||
|`Box10.Proceeds`|`number`|`extract`|Proceeds extracted from Form 1040-ScheduleD.|496|
|`Box10.Cost`|`number`|`extract`|Cost extracted from Form 1040-ScheduleD.|176|
|`Box10.Adjustments`|`number`|`extract`|Adjustments extracted from Form 1040-ScheduleD.|199.33|
|`Box10.GainOrLoss`|`number`|`extract`|Gain or loss extracted from Form 1040-ScheduleD.|128|
