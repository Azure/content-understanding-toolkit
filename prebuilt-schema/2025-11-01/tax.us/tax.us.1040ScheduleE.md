**Analyzer ID:** `prebuilt-tax.us.1040ScheduleE`

**Description:** Supplemental Income and Loss.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1040-ScheduleE.|2025|
|`Taxpayer`|`object`|`generate`|||
|`Taxpayer.SSN`|`string`|`extract`|Taxpayer tax social security number.|123-45-6789|
|`Taxpayer.Name`|`string`|`extract`|Taxpayer name as written on the form.|Pascale Wedert|
|`BoxA`|`array`|`generate`|Made any payments requiring Form(s) 1099? (Yes/No)||
|`BoxA.*`|`string`|`extract`|||
|`BoxB`|`array`|`generate`|If 'Yes' to Box A, did or will you file required Form(s) 1099? (Yes/No)||
|`BoxB.*`|`string`|`extract`|||
|`Box19ExtraInfo`|`string`|`extract`|Box 19 other (list) description.|HOA fees|
|`Box23a`|`number`|`extract`|Total of all amounts reported on line 3 for all rental properties.|150632|
|`Box23b`|`number`|`extract`|Total of all amounts reported on line 4 for all royalty properties.|13|
|`Box23c`|`number`|`extract`|Total of all amounts reported on line 12 for all properties.|965.22|
|`Box23d`|`number`|`extract`|Total of all amounts reported on line 18 for all properties.|147|
|`Box23e`|`number`|`extract`|Total of all amounts reported on line 20 for all properties.|216|
|`Box24`|`number`|`extract`|Income (add positive amounts shown on line 21; do not include losses).|965.12|
|`Box25`|`number`|`extract`|Losses (add royalty losses from line 21 and rental real estate losses from line 22).|-321|
|`Box26`|`number`|`extract`|Total rental real estate and royalty income or (loss).|196|
|`OtherPropertyDescription`|`string`|`extract`|Other property description.|Land|
|`IncomeOrLossFromRentalRealEstatePropertyDetails`|`array`|`generate`|Income or loss from rental real estate properties and royalties.||
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*`|`object`|`generate`|||
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.PhysicalAddress`|`string`|`extract`|Physical address of the property.|123 Fremont Ave, Seattle, WA 98122|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.PropertyType`|`string`|`extract`|Type of the property.|Single Family Residence|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.FairRentalDays`|`integer`|`extract`|Number of fair rental days.|365|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.PersonalUseDays`|`integer`|`extract`|Number of personal use days.|0|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.IsQJV`|`boolean`|`extract`|Qualified joint venture indicator for this property.|true|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box3`|`number`|`extract`|Rents received.|98654|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box4`|`number`|`extract`|Royalties received.|650|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box5`|`number`|`extract`|Advertising.|256|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box6`|`number`|`extract`|Auto and travel.|123|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box7`|`number`|`extract`|Cleaning and maintenance.|569.63|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box8`|`number`|`extract`|Commissions.|127|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box9`|`number`|`extract`|Insurance.|159|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box10`|`number`|`extract`|Legal and other professional fees.|452.36|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box11`|`number`|`extract`|Management fees.|12|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box12`|`number`|`extract`|Mortgage interest paid to banks, etc.|89|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box13`|`number`|`extract`|Other interest.|48|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box14`|`number`|`extract`|Repairs.|599|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box15`|`number`|`extract`|Supplies.|873|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box16`|`number`|`extract`|Taxes.|899|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box17`|`number`|`extract`|Utilities.|864|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box18`|`number`|`extract`|Depreciation expense or depletion.|436.36|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box19`|`number`|`extract`|Other (list).|1563|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box20`|`number`|`extract`|Total expenses (add lines 5 through 19).|8123|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box21`|`number`|`extract`|Subtract line 20 from line 3 and/or 4.|96123|
|`IncomeOrLossFromRentalRealEstatePropertyDetails.*.Box22`|`number`|`extract`|Deductible rental real estate loss after limitation, if any, on Form 8582.|-21|
|`Box27`|`array`|`generate`|Reporting any prior-year unallowed losses or similar (Yes/No).||
|`Box27.*`|`string`|`extract`|||
|`Box29aPassiveIncomeTotal`|`number`|`extract`|Line 29a: Passive income total.|369|
|`Box29aNonPassiveIncomeTotal`|`number`|`extract`|Line 29a: Nonpassive income total.|148|
|`Box29bPassiveLossAllowedTotal`|`number`|`extract`|Line 29b: Passive loss allowed total.|236|
|`Box29bNonPassiveLossAllowedTotal`|`number`|`extract`|Line 29b: Nonpassive loss allowed total.|432|
|`Box29bExpenseDeductionTotal`|`number`|`extract`|Line 29b: Section 179 expense deduction total.|123|
|`Box30`|`number`|`extract`|Add columns (h) and (k) of line 29a.|983.01|
|`Box31`|`number`|`extract`|Add columns (g), (i), and (j) of line 29b.|-123|
|`Box32`|`number`|`extract`|Total partnership and S corporation income or (loss).|114|
|`Box34aPassiveIncomeTotal`|`number`|`extract`|Line 34a: Passive income total.|987|
|`Box34aNonPassiveIncomeTotal`|`number`|`extract`|Line 34a: Other income total.|126|
|`Box34bPassiveLossAllowedTotal`|`number`|`extract`|Line 34b: Passive deduction or loss allowed total.|123|
|`Box34bNonPassiveLossAllowedTotal`|`number`|`extract`|Line 34b: Deduction or loss from Schedule K-1 total.|963|
|`Box35`|`number`|`extract`|Add columns (d) and (f) of line 34a.|852|
|`Box36`|`number`|`extract`|Add columns (c) and (e) of line 34b.|-321|
|`Box37`|`number`|`extract`|Total estate and trust income or (loss).|123|
|`Box39`|`number`|`extract`|Combine columns (d) and (e) only for REMICs.|963|
|`Box40`|`number`|`extract`|Net farm rental income or (loss) from Form 4835.|123|
|`Box41`|`number`|`extract`|Total income or (loss).|146|
|`Box42`|`number`|`extract`|Reconciliation of farming and fishing income.|951|
|`Box43`|`number`|`extract`|Reconciliation for real estate professionals.|159|
|`IncomeOrLossFromPartnershipDetails`|`array`|`generate`|Income or loss from partnerships and S corporations.||
|`IncomeOrLossFromPartnershipDetails.*`|`object`|`generate`|||
|`IncomeOrLossFromPartnershipDetails.*.Box28a`|`string`|`extract`|Name.|Contoso Investments LLC|
|`IncomeOrLossFromPartnershipDetails.*.Box28b`|`string`|`extract`|Enter P for partnership; S for S corporation.|P|
|`IncomeOrLossFromPartnershipDetails.*.Box28cIsForeignPartnership`|`boolean`|`extract`|Check if foreign partnership.|true|
|`IncomeOrLossFromPartnershipDetails.*.Box28d`|`string`|`extract`|Employer identification number.|98-7654321|
|`IncomeOrLossFromPartnershipDetails.*.Box28eIsBasisComputationRequired`|`boolean`|`extract`|Check if basis computation is required.|true|
|`IncomeOrLossFromPartnershipDetails.*.Box28fIsNotAtRisk`|`boolean`|`extract`|Check if any amount is not at risk.|true|
|`IncomeOrLossFromPartnershipDetails.*.Box28g`|`number`|`extract`|Passive loss allowed.|-123|
|`IncomeOrLossFromPartnershipDetails.*.Box28h`|`number`|`extract`|Passive income from Schedule K-1.|321|
|`IncomeOrLossFromPartnershipDetails.*.Box28i`|`number`|`extract`|Nonpassive loss allowed.|741|
|`IncomeOrLossFromPartnershipDetails.*.Box28j`|`number`|`extract`|Section 179 expense deduction from Form 4562.|183|
|`IncomeOrLossFromPartnershipDetails.*.Box28k`|`number`|`extract`|Nonpassive income from Schedule K-1.|148|
|`IncomeOrLossFromEstateAndTrustDetails`|`array`|`generate`|Income or loss from estates and trusts.||
|`IncomeOrLossFromEstateAndTrustDetails.*`|`object`|`generate`|||
|`IncomeOrLossFromEstateAndTrustDetails.*.Box33a`|`string`|`extract`|Name.|Contoso Estate|
|`IncomeOrLossFromEstateAndTrustDetails.*.Box33b`|`string`|`extract`|Employer identification number.|85-9632147|
|`IncomeOrLossFromEstateAndTrustDetails.*.Box33c`|`number`|`extract`|Passive deduction or loss allowed.|123|
|`IncomeOrLossFromEstateAndTrustDetails.*.Box33d`|`number`|`extract`|Passive income from Schedule K-1.|741|
|`IncomeOrLossFromEstateAndTrustDetails.*.Box33e`|`number`|`extract`|Deduction or loss from Schedule K-1.|963|
|`IncomeOrLossFromEstateAndTrustDetails.*.Box33g`|`number`|`extract`|Other income from Schedule K-1.|126|
|`IncomeOrLossFromRealEstateMortgageInvestmentDetails`|`array`|`generate`|Income or loss from REMICs (residual holder).||
|`IncomeOrLossFromRealEstateMortgageInvestmentDetails.*`|`object`|`generate`|||
|`IncomeOrLossFromRealEstateMortgageInvestmentDetails.*.Box33a`|`string`|`extract`|Name.|Contoso Real Estate LLC|
|`IncomeOrLossFromRealEstateMortgageInvestmentDetails.*.Box33b`|`string`|`extract`|Employer identification number.|74-1236589|
|`IncomeOrLossFromRealEstateMortgageInvestmentDetails.*.Box33c`|`number`|`extract`|Excess inclusion from Schedules Q, line 2c.|654|
|`IncomeOrLossFromRealEstateMortgageInvestmentDetails.*.Box33d`|`number`|`extract`|Taxable income (net loss) from Schedules Q, line 1b.|123|
|`IncomeOrLossFromRealEstateMortgageInvestmentDetails.*.Box33e`|`number`|`extract`|Income from Schedules Q, line 3b.|147|
