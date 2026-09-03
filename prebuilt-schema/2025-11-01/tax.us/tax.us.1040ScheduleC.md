**Analyzer ID:** `prebuilt-tax.us.1040ScheduleC`

**Description:** Profit or Loss from Business.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleC.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer tax social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Weydert|
|`BoxA`|`string`|`extract`|Principal business or profession, including product or service.|Resin and rubber manufacturing|
|`BoxB`|`string`|`extract`|Business code from instructions.|325200|
|`BoxC`|`string`|`extract`|Business name. If no separate business name, leave blank.|Contoso Carwash LTD|
|`BoxD`|`string`|`extract`|Employer ID number (EIN).|12-3456789|
|`BoxE`|`string`|`extract`|Business address (including suite or room no.).|123 Fremont Ave, Unit 5, Seattle WA 98122|
|`BoxF`|`array`|`generate`|Accounting method selection.||
|`BoxF.*`|`string`|`extract`|||
|`BoxFExtraInfo`|`string`|`extract`|Box F extra info (if 'Other' is selected).|Other method detail|
|`BoxG`|`array`|`generate`|Materially participate indicator (Yes/No).||
|`BoxG.*`|`string`|`extract`|||
|`BoxH`|`boolean`|`extract`|Started or acquired this business during the tax year.|true|
|`BoxI`|`array`|`generate`|Made any payments requiring Form(s) 1099 (Yes/No).||
|`BoxI.*`|`string`|`extract`|||
|`BoxJ`|`array`|`generate`|If 'Yes' to Box I, did or will you file required Form(s) 1099 (Yes/No).||
|`BoxJ.*`|`string`|`extract`|||
|`Box1IsChecked`|`boolean`|`extract`|Form W-2 statutory employee checkbox.|true|
|`Box1`|`number`|`extract`|Gross receipts or sales.|321|
|`Box2`|`number`|`extract`|Returns and allowances.|147|
|`Box3`|`number`|`extract`|Subtract line 2 from line 1.|258|
|`Box4`|`number`|`extract`|Cost of goods sold (from line 42).|745.22|
|`Box5`|`number`|`extract`|Gross profit (line 3 minus line 4).|213|
|`Box6`|`number`|`extract`|Other income.|185|
|`Box7`|`number`|`extract`|Gross income (add lines 5 and 6).|248211|
|`Box8`|`number`|`extract`|Advertising.|963|
|`Box9`|`number`|`extract`|Car and truck expenses.|123|
|`Box10`|`number`|`extract`|Commissions and fees.|147|
|`Box11`|`number`|`extract`|Contract labor.|856|
|`Box12`|`number`|`extract`|Depletion.|214|
|`Box13`|`number`|`extract`|Depreciation and section 179 expense deduction.|289|
|`Box14`|`number`|`extract`|Employee benefit programs.|853|
|`Box15`|`number`|`extract`|Insurance (other than health).|123|
|`Box16a`|`number`|`extract`|Interest: Mortgage (paid to banks, etc.).|941|
|`Box16b`|`number`|`extract`|Interest: Other.|216|
|`Box17`|`number`|`extract`|Legal and professional services.|899|
|`Box18`|`number`|`extract`|Office expense.|265|
|`Box19`|`number`|`extract`|Pension and profit-sharing plans.|213|
|`Box20a`|`number`|`extract`|Rent or lease: Vehicles, machinery, and equipment.|876|
|`Box20b`|`number`|`extract`|Rent or lease: Other business property.|218|
|`Box21`|`number`|`extract`|Repairs and maintenance.|269|
|`Box22`|`number`|`extract`|Supplies (not included in Part III).|963|
|`Box23`|`number`|`extract`|Taxes and licenses.|178|
|`Box24a`|`number`|`extract`|Travel.|321|
|`Box24b`|`number`|`extract`|Deductible meals.|951|
|`Box25`|`number`|`extract`|Utilities.|142.33|
|`Box26`|`number`|`extract`|Wages (less employment credits).|693|
|`Box27a`|`number`|`extract`|Other expenses (from line 48).|469|
|`Box27b`|`number`|`extract`|Energy efficient commercial buildings deduction.|941|
|`Box28`|`number`|`extract`|Total expenses before expenses for business use of home (add lines 8 through 27b).|123|
|`Box29`|`number`|`extract`|Tentative profit or (loss) (line 7 minus line 28).|841|
|`Box30a`|`integer`|`extract`|Simplified method: Your home's total square footage. This is a whole-number quantity (square feet); fractional values are not valid. Stored as integer.|9963|
|`Box30b`|`integer`|`extract`|Simplified method: Business-use square footage. This is a whole-number quantity (square feet); fractional values are not valid. Stored as integer.|4563|
|`Box30`|`number`|`extract`|Expenses for business use of your home.|215|
|`Box31`|`number`|`extract`|Net profit or (loss) (line 29 minus line 30).|187|
|`Box32a`|`boolean`|`extract`|All investment is at risk.|true|
|`Box32b`|`boolean`|`extract`|Some investment is not at risk.|false|
|`Box33`|`array`|`generate`|Method(s) used to value closing inventory.||
|`Box33.*`|`string`|`extract`|||
|`Box34`|`array`|`generate`|Change in determining quantities, costs, or valuations between opening and closing inventory (Yes/No).||
|`Box34.*`|`string`|`extract`|||
|`Box35`|`number`|`extract`|Inventory at beginning of year.|658|
|`Box36`|`number`|`extract`|Purchases less cost of items withdrawn for personal use.|153|
|`Box37`|`number`|`extract`|Cost of labor (do not include any amounts paid to yourself).|897|
|`Box38`|`number`|`extract`|Materials and supplies.|213|
|`Box39`|`number`|`extract`|Other costs.|489|
|`Box40`|`number`|`extract`|Add lines 35 through 39.|233|
|`Box41`|`number`|`extract`|Inventory at end of year.|117|
|`Box42`|`number`|`extract`|Cost of goods sold (line 40 minus line 41).|12233|
|`Box43`|`date`|`extract`|Vehicle placed in service date (YYYY-MM-DD).|2023-01-01|
|`Box44a`|`integer`|`extract`|Vehicle miles: Business. Whole-number count of miles; fractional miles are not valid. Stored as integer.|3654|
|`Box44b`|`integer`|`extract`|Vehicle miles: Commuting. Whole-number count of miles; fractional miles are not valid. Stored as integer.|5986|
|`Box44c`|`integer`|`extract`|Vehicle miles: Other. Whole-number count of miles; fractional miles are not valid. Stored as integer.|311|
|`Box45`|`array`|`generate`|Was your vehicle available for personal use during off-duty hours? (Yes/No)||
|`Box45.*`|`string`|`extract`|||
|`Box46`|`array`|`generate`|Do you (or your spouse) have another vehicle available for personal use? (Yes/No)||
|`Box46.*`|`string`|`extract`|||
|`Box47a`|`array`|`generate`|Do you have evidence to support your deduction? (Yes/No)||
|`Box47a.*`|`string`|`extract`|||
|`Box47b`|`array`|`generate`|If 'Yes,' is the evidence written? (Yes/No)||
|`Box47b.*`|`string`|`extract`|||
|`Box48`|`number`|`extract`|Total other expenses (enter here and on line 27a).|145|
|`OtherExpenses`|`array`|`generate`|List of other business expenses and equivalent amounts extracted from Form 1040-ScheduleC.||
|`OtherExpenses.*`|`object`|`generate`|||
|`OtherExpenses.*.Description`|`string`|`extract`|Description extracted from Form 1040-ScheduleC.|Car Wash|
|`OtherExpenses.*.Amount`|`number`|`extract`|Amount extracted from Form 1040-ScheduleC.|654|
